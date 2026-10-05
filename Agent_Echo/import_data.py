"""Load Echo's eleven public prototype datasets into a validated SQLite database.

Uses Python's standard library. Private QA datasets are never imported.
"""
import argparse
import csv
from datetime import date
import itertools
from pathlib import Path
import re
import sqlite3
import sys
import uuid


HERE = Path(__file__).resolve().parent
FILES = (
    'HR_managers.csv',
    'HR_employees.csv',
    'OP_projects.csv',
    'OP_work_requests.csv',
    'OP_capacity.csv',
    'OP_priority_decisions.csv',
    'OP_contributions.csv',
    'HR_recognition_feedback.csv',
    'HR_survey_summary.csv',
    'HR_survey_comments.csv',
    'HR_program_participation.csv',
)
INTEGER_COLUMNS = {
    'Employees_In_Original_Source', 'Pilot_Assigned_Employees',
    'Eligible_Employees', 'Responses', 'Scale_Min', 'Scale_Max',
    'Favorable_Responses', 'Promoters', 'Passives', 'Detractors',
    'Response_Score', 'Use_Count', 'Usefulness_Score',
}
REAL_COLUMNS = {
    'Favorable_Percent', 'Mean_Score', 'eNPS_Score', 'Participation_Hours',
    'Scheduled_Hours', 'Leave_Hours', 'Routine_Hours', 'Available_Project_Hours',
    'Original_Estimated_Hours', 'Current_Estimated_Hours', 'Actual_Hours',
    'Rework_Hours', 'Previous_Estimated_Hours', 'Revised_Estimated_Hours',
}


def quote_identifier(name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name):
        raise ValueError(f'Unsupported database identifier: {name!r}')
    return '"' + name + '"'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def column_type(column):
    return 'INTEGER' if column in INTEGER_COLUMNS else 'REAL' if column in REAL_COLUMNS else 'TEXT'


def prepare_schema(source):
    manifest = {row['File']: row for row in read_csv(source / 'QA_manifest.csv')}
    allowed = {name for name, row in manifest.items() if row['Load_Into_Prototype'] == 'Yes'}
    if allowed != set(FILES):
        raise ValueError('Manifest application files differ from the eleven approved datasets.')
    definitions = {}
    for row in read_csv(source / 'QA_data_dictionary.csv'):
        if row['File'] in FILES:
            definitions.setdefault(row['File'], {})[row['Column']] = row
    schemas = {}
    for filename in FILES:
        with (source / filename).open(encoding='utf-8-sig', newline='') as stream:
            columns = next(csv.reader(stream))
        if set(columns) != set(definitions.get(filename, {})) or len(columns) != len(set(columns)):
            raise ValueError(f'CSV headers do not match the dictionary: {filename}')
        key = manifest[filename]['Primary_Key']
        if [col for col in columns if definitions[filename][col]['Primary_Key'] == 'Yes'] != [key]:
            raise ValueError(f'Primary key definition does not match: {filename}')
        clauses = []
        for column in columns:
            definition = definitions[filename][column]
            clause = f'{quote_identifier(column)} {column_type(column)}'
            if definition['Nullable'] == 'No' or column == key:
                clause += ' NOT NULL'
            if column == key:
                clause += ' PRIMARY KEY'
            if definition['References']:
                target_file, target_column = definition['References'].rsplit('.', 1)
                if target_file not in FILES or target_column not in definitions[target_file]:
                    raise ValueError(f'Unapproved foreign-key target in {filename}.{column}')
                clause += f' REFERENCES {quote_identifier(Path(target_file).stem)} ({quote_identifier(target_column)})'
            clauses.append(clause)
        schemas[filename] = (columns, definitions[filename], clauses)
    return manifest, schemas


def converted_rows(reader, filename, columns, definitions):
    for line_number, row in enumerate(reader, start=2):
        if None in row or any(row.get(col) is None for col in columns):
            raise ValueError(f'Invalid CSV row width in {filename}, line {line_number}')
        values = []
        for column in columns:
            value = row[column]
            if value == '':
                if definitions[column]['Nullable'] != 'Yes':
                    raise ValueError(f'Missing required field in {filename}, line {line_number}: {column}')
                values.append(None)
                continue
            try:
                if column in INTEGER_COLUMNS:
                    value = int(value)
                elif column in REAL_COLUMNS:
                    value = float(value)
                elif column.endswith('_Date') or column == 'Week_Start':
                    if date.fromisoformat(value).isoformat() != value:
                        raise ValueError('Date is not ISO formatted')
            except ValueError:
                raise ValueError(f'Invalid value in {filename}, line {line_number}: {column}') from None
            values.append(value)
        yield tuple(values)


def build_database(source, output, replace=False):
    if output.exists() and not replace:
        raise FileExistsError('The database already exists. Use --replace to rebuild it explicitly.')
    manifest, schemas = prepare_schema(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f'{output.stem}.build-{uuid.uuid4().hex}.db')
    connection = None
    counts = {}
    try:
        connection = sqlite3.connect(temporary)
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('BEGIN')
        for filename in FILES:
            columns, definitions, clauses = schemas[filename]
            table = Path(filename).stem
            connection.execute(f'CREATE TABLE {quote_identifier(table)} ({", ".join(clauses)})')
            sql = f'INSERT INTO {quote_identifier(table)} ({", ".join(map(quote_identifier, columns))}) VALUES ({", ".join("?" for _ in columns)})'
            count = 0
            with (source / filename).open(encoding='utf-8-sig', newline='') as stream:
                rows = converted_rows(csv.DictReader(stream), filename, columns, definitions)
                while batch := list(itertools.islice(rows, 2000)):
                    connection.executemany(sql, batch)
                    count += len(batch)
            if count != int(manifest[filename]['Rows']):
                raise ValueError(f'Row count differs from the manifest: {filename}')
            counts[table] = count
            print(f'{table}: {count:,} rows', flush=True)
        for filename, (columns, definitions, _) in schemas.items():
            table = Path(filename).stem
            for column in columns:
                if definitions[column]['References']:
                    index = f'idx_{table}_{column}'
                    connection.execute(f'CREATE INDEX {quote_identifier(index)} ON {quote_identifier(table)} ({quote_identifier(column)})')
        for table, columns in {
            'HR_survey_summary': ('Team', 'Survey_Date'),
            'HR_program_participation': ('Team', 'Period_Start_Date'),
            'HR_recognition_feedback': ('Employee_ID', 'Interaction_Date'),
            'OP_capacity': ('Employee_ID', 'Week_Start'),
            'OP_contributions': ('Employee_ID', 'Contribution_Date'),
            'OP_work_requests': ('Assigned_Employee_ID', 'Week_Start'),
        }.items():
            connection.execute(f'CREATE INDEX {quote_identifier("idx_" + table + "_period")} ON {quote_identifier(table)} ({", ".join(map(quote_identifier, columns))})')
        if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise ValueError('Database foreign-key validation failed.')
        connection.commit()
        if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('SQLite integrity validation failed.')
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if tables != {Path(name).stem for name in FILES}:
            raise ValueError('Database contains an unexpected table.')
        if any(connection.execute(f'SELECT COUNT(*) FROM {quote_identifier(table)}').fetchone()[0] != count for table, count in counts.items()):
            raise ValueError('Saved table counts do not match imported rows.')
        connection.close()
        connection = None
        temporary.replace(output)
    except Exception:
        if connection is not None:
            connection.close()
        temporary.unlink(missing_ok=True)
        temporary.with_name(temporary.name + '-journal').unlink(missing_ok=True)
        raise
    print(f'Imported {sum(counts.values()):,} rows into {output}', flush=True)
    print('Validation: eleven tables, matching row counts, valid references, SQLite integrity OK.')
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=HERE.parent / 'files_update')
    parser.add_argument('--database', type=Path, default=HERE / 'data' / 'echo.db')
    parser.add_argument('--replace', action='store_true', help='Replace an existing database only after the new import validates.')
    args = parser.parse_args()
    try:
        build_database(args.source.resolve(), args.database.resolve(), args.replace)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f'Import failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

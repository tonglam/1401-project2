import math
import os
import csv
import random
import sqlite3
import numpy as np
import scipy.stats as stats
from domain.Organisations import Organisations
from faker import Faker
import string
import solution as solution

default_csvfile = "./Organisations.csv"
default_db = "./Organisations.db"
fake = Faker()


def get_headers() -> str:
    with open(default_csvfile, 'r') as f:
        read_data = f.readlines()
        header = read_data[0].lower().strip().split(',')
    return ",".join(header) + "\n"


def fake_organisations_data(organisation_id: str = "", name: str = "", website: str = "", country: str = "",
                            founded: int = 0, category: str = "", number_of_employees: int = 0, median_salary: int = 0,
                            profits_in_2020_million: int = 0, profits_in_2021_million: int = 0) -> Organisations:
    organisation_record = Organisations(
        organisation_id=''.join(random.choices(string.hexdigits.lower(), k=15)) if len(
            organisation_id) == 0 else organisation_id,
        name=fake.name() if len(name) == 0 else name,
        website=fake.url() if len(website) == 0 else website,
        country='test_' + fake.country() if len(country) == 0 else country,
        founded=fake.year() if founded == 0 else founded,
        category=fake.word() if len(category) == 0 else category,
        number_of_employees=random.randint(1, 1000) if number_of_employees == 0 else number_of_employees,
        median_salary=random.randint(1, 1000000) if median_salary == 0 else median_salary,
        profits_in_2020_million=random.randint(1, 1000000) if profits_in_2020_million == 0 else profits_in_2020_million,
        profits_in_2021_million=random.randint(1, 1000000) if profits_in_2021_million == 0 else profits_in_2021_million
    )
    return organisation_record


def import_data(cursor: sqlite3.Cursor, conn: sqlite3.Connection, csvfile: str = default_csvfile) -> None:
    # create table
    cursor.execute("DROP TABLE IF EXISTS Organisations;")
    cursor.execute('''
                    CREATE TABLE Organisations
                    (
                        "organisation id"          TEXT NOT NULL,
                        name                       TEXT NOT NULL,
                        website                    TEXT NOT NULL,
                        country                    TEXT NOT NULL,
                        founded                    INTEGER NOT NULL,
                        category                   TEXT NOT NULL,
                        "number of employees"      INTEGER NOT NULL,
                        "median salary"            REAL NOT NULL,
                        "profits in 2020(million)" REAL NOT NULL,
                        "profits in 2021(million)" REAL NOT NULL
                    );
                ''')
    cursor.execute("DROP VIEW IF EXISTS CountryOrganisations;")
    cursor.execute('''
                    CREATE VIEW CountryOrganisations AS
                    SELECT country, 
                           sum("number of employees") AS "number of employees", 
                           sum("median Salary") AS "median Salary", 
                           sum("profits in 2020(million)") AS "profits in 2020(million)", 
                           sum("profits in 2021(million)") AS "profits in 2021(million)"
                    FROM Organisations
                    GROUP BY country;
                    ''')
    cursor.execute("DROP VIEW IF EXISTS CategoryOrganisations;")
    cursor.execute('''
                    CREATE VIEW CategoryOrganisations AS
                    SELECT  category,
                            "organisation id",
                            "number of employees",
                            "median Salary",
                            round(abs("profits in 2020(million)" - "profits in 2021(million)") / ("profits in 2020(million)" * 1.0) * 100, 4) AS "profit percent change"
                    FROM Organisations
                    GROUP BY category, "organisation id";
                    ''')
    cursor.execute("DROP TABLE IF EXISTS Output_1;")
    cursor.execute('''
                    CREATE TABLE Output_1
                    (
                        country                    TEXT,
                        t_test_score               REAL DEFAULT 0,
                        distance                   REAL DEFAULT 0,
                        primary key (country)
                    );
                  ''')
    cursor.execute("DROP TABLE IF EXISTS Output_2;")
    cursor.execute('''
                    CREATE TABLE Output_2
                    (
                      category                   TEXT,
                      "organisation id"          TEXT,
                      "number of employees"      INTEGER DEFAULT 0,
                      "profit percent change"    REAL DEFAULT 0,
                      rank                       INTEGER DEFAULT 0,
                      primary key (category, "organisation id")
                    );
                  ''')
    conn.commit()

    # clean csv
    if os.path.exists("cleaned.csv"):
        os.remove("cleaned.csv")
    with open(csvfile, 'r') as f:
        read_data = f.readlines()
    # get csv header
    if len(read_data) == 0:
        return
    header = read_data[0].lower().strip().split(',')
    csv_data = []
    # save to a dictionary list
    organisation_id_set = set()
    organisation_duplicate_id_set = set()
    for i in range(1, len(read_data)):
        line = read_data[i].lower().strip()
        # empty line
        if len(line) == 0:
            continue
        data = line.split(',')
        # save to a dictionary
        data_dict = dict(zip(header, data))
        # check data type
        if invalid(data_dict):
            continue
        # get organisation id
        organisation_id = data_dict['organisation id']
        if organisation_id not in organisation_id_set:
            organisation_id_set.add(organisation_id)
        elif organisation_id not in organisation_duplicate_id_set:
            organisation_duplicate_id_set.add(organisation_id)
        csv_data.append(data_dict)
    clean_file = "cleaned.csv"
    if organisation_duplicate_id_set.__contains__(""):
        organisation_duplicate_id_set.remove("")
    if len(organisation_duplicate_id_set) > 0:
        csv_data = [x for x in csv_data if x['organisation id'] not in organisation_duplicate_id_set]
    write_data = [",".join(header) + "\n"] + [",".join(x.values()) + "\n" for x in csv_data]
    with open(clean_file, 'w') as f:
        f.writelines(write_data)

    # import clean data
    column_order_list = ['organisation id', 'name', 'website', 'country', 'founded', 'category', 'number of employees',
                         'median salary', 'profits in 2020(million)', 'profits in 2021(million)']
    with open(clean_file, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)
        csv_data = list(reader)
        for row in csv_data:
            try:
                row_dict = dict(zip(header, row))
                processed_row = []
                for key in column_order_list:
                    value = row_dict[key]
                    if value == '':
                        processed_row.append(None)
                    else:
                        processed_row.append(value)
                cursor.execute('INSERT INTO Organisations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);', processed_row)
                conn.commit()
            except sqlite3.Error:
                print("Error: insert data failed: {}".format(row))


def invalid(data_dict: dict) -> bool:
    # check organisation id, alphanumeric only
    if not data_dict['organisation id'].isalnum():
        return True
    # check number of employees, integer only
    if not data_dict['number of employees'].isnumeric():
        return True


def get_duplicated_organisation_id(csvfile: str) -> set:
    with open(csvfile, 'r') as f:
        read_data = f.readlines()
    # get csv header
    header = read_data[0].lower().strip().split(',')
    # save to a dictionary list
    organisation_id_set = set()
    organisation_duplicate_id_set = set()
    for i in range(1, len(read_data)):
        line = read_data[i].lower().strip()
        # empty line
        if len(line) == 0:
            continue
        data = line.split(',')
        # save to a dictionary
        data_dict = dict(zip(header, data))
        # get organisation id
        organisation_id = data_dict['organisation id']
        if organisation_id not in organisation_id_set:
            organisation_id_set.add(organisation_id)
        elif organisation_id not in organisation_duplicate_id_set:
            organisation_duplicate_id_set.add(organisation_id)
    return organisation_duplicate_id_set


def expected_t_test_score_minkowski_distance_data(cursor: sqlite3.Cursor, conn: sqlite3.Connection,
                                                  actual_country_size: int) -> None:
    # check country size
    cursor.execute('SELECT DISTINCT country FROM Organisations;')
    expected_country_list = [x[0] for x in cursor.fetchall()]
    expected_country_size = len(expected_country_list)
    assert expected_country_size == actual_country_size, "country_list length is not correct, expected:[{}], actual:[{}]".format(
        expected_country_size, actual_country_size)
    # insert expected data
    expected_output_1_list = []
    for expected_country in expected_country_list:
        # t_test_score
        cursor.execute('SELECT "profits in 2020(million)" FROM Organisations WHERE country = ?;', (expected_country,))
        expected_profit_2020_list = [x[0] for x in cursor.fetchall()]
        cursor.execute('SELECT "profits in 2021(million)" FROM Organisations WHERE country = ?;', (expected_country,))
        expected_profit_2021_list = [x[0] for x in cursor.fetchall()]
        expected_t_test_score = stats.ttest_ind(expected_profit_2020_list, expected_profit_2021_list)[0]
        expected_t_test_score = round(expected_t_test_score, 4) if (
                not math.isnan(expected_t_test_score) and not math.isinf(
            abs(expected_t_test_score))) else 0
        # Minkowski distance
        cursor.execute('SELECT "number of employees" FROM Organisations WHERE country = ?;', (expected_country,))
        expected_number_of_employees_list = np.array([x[0] for x in cursor.fetchall()])
        cursor.execute('SELECT "median salary" FROM Organisations WHERE country = ?;', (expected_country,))
        expected_median_salary_list = np.array([x[0] for x in cursor.fetchall()])
        expected_distance = np.linalg.norm(expected_number_of_employees_list - expected_median_salary_list, ord=3)
        expected_distance = round(expected_distance, 4) if (
                not math.isnan(expected_distance) and not math.isinf(abs(expected_distance))) else 0
        expected_output_1_list.append((expected_country, expected_t_test_score, expected_distance))
    cursor.executemany('INSERT INTO Output_1 VALUES (?, ?, ?);', expected_output_1_list)
    conn.commit()


def check_t_test_score_minkowski_distance(cursor: sqlite3.Cursor, actual_country_dict: dict) -> None:
    # check each country
    for actual_country, actual_country_data in actual_country_dict.items():
        cursor.execute('SELECT t_test_score, distance FROM Output_1 WHERE country = ?;', (actual_country,))
        expected_country_data = cursor.fetchone()
        # check t_test_score
        expected_t_test_score = expected_country_data[0]
        actual_t_test_score = actual_country_data[0]
        assert expected_t_test_score == actual_t_test_score, "country:[{}], t_test_score is not correct, expected:[{}], actual:[{}]".format(
            actual_country, expected_t_test_score, actual_t_test_score)
        # check minkowski_distance
        expected_distance = expected_country_data[1]
        actual_distance = actual_country_data[1]
        assert expected_distance == actual_distance, "country:[{}], minkowski_distance is not correct, expected:[{}], actual:[{}]".format(
            actual_country, expected_distance, actual_distance)


def expected_category_dict_data(cursor: sqlite3.Cursor, conn: sqlite3.Connection, actual_category_dict: dict) -> None:
    # check category size
    cursor.execute('SELECT DISTINCT category FROM Organisations;')
    expected_category_list = [x[0] for x in cursor.fetchall()]
    expected_category_size = len(expected_category_list)
    actual_category_size = len(actual_category_dict)
    assert expected_category_size == actual_category_size, "country_list length is not correct, expected:[{}], actual:[{}]".format(
        expected_category_size, actual_category_size)
    # insert expected data
    expected_output_2_list = []
    for expected_category in expected_category_list:
        # check category organisation size
        cursor.execute('SELECT DISTINCT "organisation id" FROM Organisations WHERE category = ?;', (expected_category,))
        expected_organisation_list = [x[0] for x in cursor.fetchall()]
        expected_organisation_size = len(expected_organisation_list)
        actual_organisation_size = len(actual_category_dict[expected_category])
        assert expected_organisation_size == actual_organisation_size, "category:[{}], organisation_list length is not correct, expected:[{}], actual:[{}]".format(
            expected_category, expected_organisation_size, actual_organisation_size)
        # each organisation
        for expected_organisation in expected_organisation_list:
            # expected rank
            cursor.execute('''
                                select "organisation id", RANK() OVER (ORDER BY "number of employees" DESC, "profit percent change" DESC) AS rank
                                from CategoryOrganisations
                                where category = ?
                                order by "number of employees" desc, "absolute profit change" desc;
                           ''', (expected_category,))
            expected_rank_list = cursor.fetchall()
            expected_rank_dict = dict(expected_rank_list)
            # get expected data
            cursor.execute(
                'SELECT "number of employees", "profit percent change" FROM CategoryOrganisations WHERE category = ? AND "organisation id" = ?;',
                (expected_category, expected_organisation))
            expected_data = cursor.fetchone()
            expected_data = (expected_category, expected_organisation, expected_data[0], expected_data[1],
                             expected_rank_dict[expected_organisation])
            expected_output_2_list.append(expected_data)
    cursor.executemany('INSERT INTO Output_2 VALUES (?, ?, ?, ?, ?);', expected_output_2_list)
    conn.commit()


def check_category_dictionary(cursor: sqlite3.Cursor, actual_category_dict: dict) -> None:
    for actual_category, actual_category_data in actual_category_dict.items():
        for actual_organisation, actual_data in actual_category_data.items():
            cursor.execute(
                'SELECT "number of employees", "profit percent change", rank FROM Output_2 WHERE category = ? AND "organisation id" = ?;',
                (actual_category, actual_organisation))
            expected_data = cursor.fetchone()
            assert expected_data[0] == actual_data[
                0], "category:[{}], organisation:[{}], numbers of employees is not correct, expected:[{}], actual:[{}]".format(
                actual_category, actual_organisation, expected_data[0], actual_data[0])
            assert expected_data[1] == actual_data[
                1], "category:[{}], organisation:[{}], percentage of profit change from 2020 to 2021 (absolute value) is not correct, expected:[{}], actual:[{}]".format(
                actual_category, actual_organisation, expected_data[1], actual_data[1])
            assert expected_data[2] == actual_data[
                2], "category:[{}], organisation:[{}], rank is not correct, expected:[{}], actual:[{}]".format(
                actual_category, actual_organisation, expected_data[2], actual_data[2])


def check_empty_with_header_file() -> None:
    # empty input file with header
    empty_with_header_file = "./empty_with_header.csv"
    # check file exists
    if os.path.exists(empty_with_header_file):
        os.remove(empty_with_header_file)
    # get default header
    header = get_headers()
    # write file
    with open(empty_with_header_file, 'w') as f:
        f.write(header)
    # run test
    run_test_case(empty_with_header_file)
    # remove file
    os.remove(empty_with_header_file)


def check_empty_without_header_file() -> None:
    # empty input file without header
    empty_without_header_file = "./empty_without_header.csv"
    # check file exists
    if os.path.exists(empty_without_header_file):
        os.remove(empty_without_header_file)
    # write file
    with open(empty_without_header_file, 'w') as f:
        f.write("")
    # run test
    run_test_case(empty_without_header_file)
    # remove file
    os.remove(empty_without_header_file)


def check_case_insensitive_header_file() -> None:
    # input file with case-insensitive header
    case_insensitive_header_file = "./case_insensitive_header.csv"
    # check file exists
    if os.path.exists(case_insensitive_header_file):
        os.remove(case_insensitive_header_file)
    # change original header to random upper case
    with open(default_csvfile, 'r') as f:
        read_data = f.readlines()
        header = read_data[0].lower().strip().split(',')
    # random upper case
    for i in range(5):
        sample_index = np.random.randint(0, len(header))
        header[sample_index] = header[sample_index].upper()
    read_data = [",".join(header) + "\n"] + read_data[1:]
    # write file
    with open(case_insensitive_header_file, 'w') as f:
        f.writelines(read_data)
    # run test
    run_test_case(case_insensitive_header_file)
    # remove file
    os.remove(case_insensitive_header_file)


def check_change_numeric_type_file() -> None:
    # input file with change numeric type
    change_numeric_type_file = "./change_numeric_type.csv"
    # check file exists
    if os.path.exists(change_numeric_type_file):
        os.remove(change_numeric_type_file)
    header = get_headers()
    header_list = header.lower().strip().split(',')
    write_data = [header]
    # random change numeric value to float
    with open(default_csvfile, 'r') as f:
        read_data = f.readlines()
        data_list = read_data[1:]
        for i in range(5):
            sample_index = np.random.randint(0, len(data_list))
            sample_data = data_list[sample_index]
            sample_data_list = sample_data.lower().strip().split(',')
            sample_data_dict = dict(zip(header_list, sample_data_list))
            sample_data_dict['number of employees'] = str(float(sample_data_dict['number of employees']) + 0.5)
            sample_data = ",".join(sample_data_dict.values()) + "\n"
            write_data.append(sample_data)
        for i in range(5):
            sample_index = np.random.randint(0, len(data_list))
            sample_data = data_list[sample_index]
            sample_data_list = sample_data.lower().strip().split(',')
            sample_data_dict = dict(zip(header_list, sample_data_list))
            sample_data_dict['median salary'] = str(float(sample_data_dict['median salary']) + 0.5)
            sample_data_dict['profits in 2020(million)'] = str(
                float(sample_data_dict['profits in 2020(million)']) + 0.5)
            sample_data_dict['profits in 2021(million)'] = str(
                float(sample_data_dict['profits in 2021(million)']) + 0.5)
            sample_data = ",".join(sample_data_dict.values()) + "\n"
            write_data.append(sample_data)
    # write file
    with open(change_numeric_type_file, 'w') as f:
        f.writelines(write_data)
    # run test
    run_test_case(change_numeric_type_file)
    # # remove file
    os.remove(change_numeric_type_file)


def check_missing_values_file() -> None:
    # input file with missing values
    missing_values_file = "./missing_values.csv"
    # check file exists
    if os.path.exists(missing_values_file):
        os.remove(missing_values_file)
    # randomly omit some values
    csv_data = []
    with open(default_csvfile, 'r') as f:
        read_data = f.readlines()
        header = read_data[0]
        csv_data.append(header)
    # random change
    data = read_data[1:]
    sample_index_list = random.choices(range(len(data)), k=100)
    for sample_data_index in random.sample(sample_index_list, 20):
        # organisation id, TEXT
        sample_data = data[sample_data_index]
        sample_data = sample_data.replace("\n", "")
        sample_data = sample_data.split(',')
        sample_data[0] = ''
        sample_data = ",".join(str(x) for x in sample_data) + "\n"
        data[sample_data_index] = sample_data
    for sample_data_index in random.sample(sample_index_list, 20):
        # country, TEXT
        sample_data = data[sample_data_index]
        sample_data = sample_data.replace("\n", "")
        sample_data = sample_data.split(',')
        sample_data[3] = ''
        sample_data = ",".join(str(x) for x in sample_data) + "\n"
        data[sample_data_index] = sample_data
    for sample_data_index in random.sample(sample_index_list, 20):
        # category, TEXT
        sample_data = data[sample_data_index]
        sample_data = sample_data.replace("\n", "")
        sample_data = sample_data.split(',')
        sample_data[5] = ''
        sample_data = ",".join(str(x) for x in sample_data) + "\n"
        data[sample_data_index] = sample_data
    for sample_data_index in random.sample(sample_index_list, 20):
        # number of employees, INTEGER
        sample_data = data[sample_data_index]
        sample_data = sample_data.replace("\n", "")
        sample_data = sample_data.split(',')
        sample_data[6] = ''
        sample_data = ",".join(str(x) for x in sample_data) + "\n"
        data[sample_data_index] = sample_data
    for sample_data_index in random.sample(sample_index_list, 20):
        # median salary, INTEGER
        sample_data = data[sample_data_index]
        sample_data = sample_data.replace("\n", "")
        sample_data = sample_data.split(',')
        sample_data[7] = ''
        sample_data = ",".join(str(x) for x in sample_data) + "\n"
        data[sample_data_index] = sample_data
    for sample_data_index in random.sample(sample_index_list, 20):
        # profits in 2020(million), INTEGER
        sample_data = data[sample_data_index]
        sample_data = sample_data.replace("\n", "")
        sample_data = sample_data.split(',')
        sample_data[8] = ''
        sample_data = ",".join(str(x) for x in sample_data) + "\n"
        data[sample_data_index] = sample_data
    for sample_data_index in random.sample(sample_index_list, 20):
        # profits in 2021(million), INTEGER
        sample_data = data[sample_data_index]
        sample_data = sample_data.replace("\n", "")
        sample_data = sample_data.split(',')
        sample_data[9] = ''
        sample_data = ",".join(str(x) for x in sample_data) + "\n"
        data[sample_data_index] = sample_data
    csv_data.extend(data)
    # write file
    with open(missing_values_file, 'w') as f:
        f.writelines(csv_data)
    # run test
    run_test_case(missing_values_file)
    # remove file
    os.remove(missing_values_file)


def check_duplicate_organisation_id_file() -> None:
    # input file with duplicate organisation id
    duplicate_organisation_id_file = "./duplicate_organisation_id.csv"
    # check file exists
    if os.path.exists(duplicate_organisation_id_file):
        os.remove(duplicate_organisation_id_file)
    # create data
    write_data = [get_headers()]
    organisations_record_1 = fake_organisations_data()
    write_data.append(organisations_record_1.__str__())
    write_data.append(organisations_record_1.__str__())
    organisations_record_2 = fake_organisations_data()
    write_data.append(organisations_record_2.__str__())
    write_data.append(organisations_record_2.__str__())
    write_data.append(organisations_record_2.__str__())
    organisations_record_3 = fake_organisations_data()
    write_data.append(organisations_record_3.__str__())
    write_data.append(organisations_record_3.__str__())
    write_data.append(organisations_record_3.__str__())
    write_data.append(organisations_record_3.__str__())
    organisations_record_4 = fake_organisations_data()
    write_data.append(organisations_record_4.__str__())
    organisations_record_5 = fake_organisations_data()
    write_data.append(organisations_record_5.__str__())
    # write file
    with open(duplicate_organisation_id_file, 'w') as f:
        f.writelines(write_data)
    # run test
    run_test_case(duplicate_organisation_id_file)
    # remove file
    os.remove(duplicate_organisation_id_file)


def check_disordered_header_file() -> None:
    # input file with disordered header
    disordered_header_file = "./disordered_header.csv"
    # check file exists
    if os.path.exists(disordered_header_file):
        os.remove(disordered_header_file)
    # change header order
    write_data = []
    with open(default_csvfile, 'r') as f:
        read_data = f.readlines()
        header = read_data[0].lower().strip().split(',')
        data = read_data[1:]
        index_list = list(range(len(header)))
        random.shuffle(index_list)
    new_header = [header[i] for i in index_list]
    write_data.append(",".join(new_header) + "\n")
    for line in data:
        line_list = line.strip().split(',')
        line_data = [line_list[i] for i in index_list]
        write_data.append(",".join(line_data) + "\n")
    # write file
    with open(disordered_header_file, 'w') as f:
        f.writelines(write_data)
    # run test
    run_test_case(disordered_header_file)
    # remove file
    os.remove(disordered_header_file)


def check_edge_test_cases() -> None:
    # input file with edge cases
    edge_cases_file = "./edge_cases.csv"
    # check file exists
    write_data = [get_headers()]
    if os.path.exists(edge_cases_file):
        os.remove(edge_cases_file)
    country_dict_cases_list = create_country_dict_edge_test_cases()
    if len(country_dict_cases_list) > 0:
        for country_dict_case in country_dict_cases_list:
            write_data.append(country_dict_case.__str__())
    category_dict_cases_list = create_category_dict_edge_test_cases()
    if len(category_dict_cases_list) > 0:
        for category_dict_case in category_dict_cases_list:
            write_data.append(category_dict_case.__str__())
    # write file
    with open(edge_cases_file, 'w') as f:
        f.writelines(write_data)
    # run test
    run_test_case(edge_cases_file)
    # remove file
    os.remove(edge_cases_file)


def create_country_dict_edge_test_cases() -> list:
    edge_test_cases_list = []

    # country contains only one organisation
    organisations_record_1_1 = fake_organisations_data(country="test_country_1")
    edge_test_cases_list.append(organisations_record_1_1)

    # profit 2020 sd and profit 2021 sd eq 0
    organisations_record_2_1 = fake_organisations_data(country="test_country_2")
    edge_test_cases_list.append(organisations_record_2_1)
    profit_2020 = organisations_record_2_1.profits_in_2020_million
    profit_2021 = organisations_record_2_1.profits_in_2021_million
    organisations_record_2_2 = fake_organisations_data(country="test_country_2")
    organisations_record_2_2.set_profits_in_2020_million(profit_2020)
    organisations_record_2_2.set_profits_in_2021_million(profit_2021)
    edge_test_cases_list.append(organisations_record_2_2)
    organisations_record_2_3 = fake_organisations_data(country="test_country_2")
    organisations_record_2_3.set_profits_in_2020_million(profit_2020)
    organisations_record_2_3.set_profits_in_2021_million(profit_2021)
    edge_test_cases_list.append(organisations_record_2_3)

    # every number of employees eq median salary
    organisations_record_4_1 = fake_organisations_data(country="test_country_3")
    edge_test_cases_list.append(organisations_record_4_1)
    organisations_record_4_1.set_median_salary(organisations_record_4_1.get_number_of_employees())
    organisations_record_4_2 = fake_organisations_data(country="test_country_3")
    organisations_record_4_2.set_median_salary(organisations_record_4_2.get_number_of_employees())
    edge_test_cases_list.append(organisations_record_4_2)
    organisations_record_4_3 = fake_organisations_data(country="test_country_3")
    organisations_record_4_3.set_median_salary(organisations_record_4_3.get_number_of_employees())
    edge_test_cases_list.append(organisations_record_4_3)

    return edge_test_cases_list


def create_category_dict_edge_test_cases() -> list:
    edge_test_cases_list = []

    # multiple same number of employees
    organisations_record_1_1 = fake_organisations_data(category="test_category_1")
    edge_test_cases_list.append(organisations_record_1_1)
    organisations_record_1_2 = fake_organisations_data(category="test_category_1")
    organisations_record_1_2.set_number_of_employees(organisations_record_1_1.get_number_of_employees())
    edge_test_cases_list.append(organisations_record_1_2)
    organisations_record_1_3 = fake_organisations_data(category="test_category_1")
    organisations_record_1_3.set_number_of_employees(organisations_record_1_1.get_number_of_employees())
    edge_test_cases_list.append(organisations_record_1_3)

    # multiple same profit change
    organisations_record_2_1 = fake_organisations_data(category="test_category_2")
    edge_test_cases_list.append(organisations_record_2_1)
    organisations_record_2_2 = fake_organisations_data(category="test_category_2")
    organisations_record_2_2.set_profits_in_2020_million(organisations_record_2_1.get_profits_in_2020_million())
    organisations_record_2_2.set_profits_in_2021_million(organisations_record_2_1.get_profits_in_2021_million())
    edge_test_cases_list.append(organisations_record_2_2)
    organisations_record_2_3 = fake_organisations_data(category="test_category_2")
    organisations_record_2_3.set_profits_in_2020_million(organisations_record_2_1.get_profits_in_2020_million())
    organisations_record_2_3.set_profits_in_2021_million(organisations_record_2_1.get_profits_in_2021_million())
    edge_test_cases_list.append(organisations_record_2_3)

    return edge_test_cases_list


def run_test_case(csvfile: str = default_csvfile) -> None:
    print("Start testing\n")
    conn = sqlite3.connect(default_db)
    cursor = conn.cursor()
    # check
    actual_country_dict, actual_category_dict = solution.main(csvfile)
    if len(actual_country_dict) == 0 or len(actual_category_dict) == 0:
        print("solution: No data is returned")
    # import file data as a sqlite database
    import_data(cursor, conn, csvfile)
    # t_test_score and minkowski_distance
    expected_t_test_score_minkowski_distance_data(cursor, conn, len(actual_country_dict))
    check_t_test_score_minkowski_distance(cursor, actual_country_dict)
    # category dictionary
    expected_category_dict_data(cursor, conn, actual_category_dict)
    check_category_dictionary(cursor, actual_category_dict)
    # result
    print("Congratulations! Pass all the tests!! Well done!!!\n")
    cursor.close()
    conn.close()


# test 1: test one case
def test_one_case() -> None:
    print("\nstart testing one case\n")
    # test
    run_test_case()
    print("finish testing one case")
    if os.path.exists("cleaned.csv"):
        os.remove("cleaned.csv")


# test 2: test special files
def test_special_files() -> None:
    print("\nstart testing special file\n")
    # test
    check_empty_with_header_file()
    check_empty_without_header_file()
    check_case_insensitive_header_file()
    check_change_numeric_type_file()
    check_missing_values_file()
    check_duplicate_organisation_id_file()
    check_disordered_header_file()
    print("finish testing special file")
    if os.path.exists("cleaned.csv"):
        os.remove("cleaned.csv")


# test 3: test edge cases
def test_edge_cases() -> None:
    print("\nstart testing edge cases\n")
    # test
    check_edge_test_cases()
    print("finish testing edge cases")
    if os.path.exists("cleaned.csv"):
        os.remove("cleaned.csv")


def test() -> None:
    test_one_case()
    test_special_files()
    test_edge_cases()

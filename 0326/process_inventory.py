SOURCE_FILE = 'Mars_Base_Inventory_List.csv'
DANGER_FILE = 'Mars_Base_Inventory_danger.csv'
FLAMMABILITY_THRESHOLD = 0.7


def parse_csv_line(line):
    return [item.strip() for item in line.strip().split(',')]


def print_file_contents(file_path):
    try:
        with open(file_path, mode='r', encoding='utf-8', newline='') as file:
            print('=== Mars_Base_Inventory_List.csv Contents ===')
            for line in file:
                print(line.rstrip('\n'))
            print()
    except OSError as error:
        print(f'File read error: {error}')
        return False
    return True


def load_inventory_as_list(file_path):
    inventory_list = []
    try:
        with open(file_path, mode='r', encoding='utf-8', newline='') as file:
            lines = file.readlines()
            if not lines:
                return []

            header = parse_csv_line(lines[0])
            for line in lines[1:]:
                stripped_line = line.strip()
                if stripped_line == '':
                    continue

                values = parse_csv_line(stripped_line)
                if len(values) != len(header):
                    continue

                try:
                    flammability = float(values[4])
                except ValueError:
                    continue

                inventory_item = {
                    'Substance': values[0],
                    'Weight (g/cm³)': values[1],
                    'Specific Gravity': values[2],
                    'Strength': values[3],
                    'Flammability': flammability,
                }
                inventory_list.append(inventory_item)
    except OSError as error:
        print(f'File read error: {error}')
        return []

    return inventory_list


def sort_by_flammability(inventory_list):
    return sorted(
        inventory_list,
        key=lambda item: item['Flammability'],
        reverse=True
    )


def filter_dangerous_items(inventory_list, threshold):
    dangerous_items = []
    for item in inventory_list:
        if item['Flammability'] >= threshold:
            dangerous_items.append(item)
    return dangerous_items


def print_inventory_list(title, inventory_list):
    print(title)
    for item in inventory_list:
        print(
            f"{item['Substance']}, "
            f"{item['Weight (g/cm³)']}, "
            f"{item['Specific Gravity']}, "
            f"{item['Strength']}, "
            f"{item['Flammability']}"
        )
    print()


def save_dangerous_items_to_csv(file_path, dangerous_items):
    try:
        with open(file_path, mode='w', encoding='utf-8', newline='') as file:
            file.write(
                'Substance,Weight (g/cm³),Specific Gravity,Strength,Flammability\n'
            )
            for item in dangerous_items:
                line = (
                    f"{item['Substance']},"
                    f"{item['Weight (g/cm³)']},"
                    f"{item['Specific Gravity']},"
                    f"{item['Strength']},"
                    f"{item['Flammability']}\n"
                )
                file.write(line)
    except OSError as error:
        print(f'File save error: {error}')
        return False
    return True


def main():
    if not print_file_contents(SOURCE_FILE):
        return

    inventory_list = load_inventory_as_list(SOURCE_FILE)
    if not inventory_list:
        print('Failed to convert the inventory list.')
        return

    print('=== Python list conversion result ===')
    print(inventory_list)
    print()

    sorted_inventory = sort_by_flammability(inventory_list)
    print_inventory_list(
        '=== Sorted by flammability (descending) ===',
        sorted_inventory
    )

    dangerous_items = filter_dangerous_items(
        sorted_inventory,
        FLAMMABILITY_THRESHOLD
    )
    print_inventory_list(
        f'=== Items with flammability >= {FLAMMABILITY_THRESHOLD} ===',
        dangerous_items
    )

    if save_dangerous_items_to_csv(DANGER_FILE, dangerous_items):
        print(f'{DANGER_FILE} saved successfully.')


if __name__ == '__main__':
    main()

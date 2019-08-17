import csv
prompt = '''Enter 'chars' to work on characters (the default),
      'moves' to work on moves,
      'read' to get a list entries in the current workspace,
      'add' to add a new entry to the current workspace,
      'delete' to delete an entry from the current workspace,
   or 'quit' to close the program
(Don't worry about capitalization throughout the course of this program)
        '''
attributes = dict(char = ['Name', 'HP', 'Speed', 'Defense'], move = ['Name', 'Lower Damage', 'Upper Damage', 'Accuracy', 'Status Effect'])
files = dict(char = 'characters.csv', move = 'moves.csv')

def print_rows(rows, fieldnames):
    print(*fieldnames, sep='\t\t')
    for row in rows:
        for field in fieldnames:
            print(row[field], end='\t\t')
        print()

def add_entry(workspace):
    with open(files[workspace], 'a', newline='') as csvfile:
        fieldnames = attributes[workspace]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        entry = {}
        for field in fieldnames:
            entry[field] = input(field + ': ').title()
        writer.writerow(entry)

def read_file(workspace):
    with open(files[workspace], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        print_rows(reader, fieldnames = reader.fieldnames)

def delete_entry(workspace):
    entryName = input('What character would you like to delete? ').title()
    rows = []
    deleted = []
    with open(files[workspace], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['Name'] == entryName:
                deleted.append(row)
            else:
                rows.append(row)
        fieldnames = reader.fieldnames
    with open(files[workspace], 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print('Successfully deleted the following entries:')
    print_rows(deleted, fieldnames)

def main():
    action = input(prompt).lower()
    workspace = 'char'
    while action != 'quit':
        if action == 'read':
            read_file(workspace)
        elif action == 'add':
            add_entry(workspace)
        elif action == 'delete':
            delete_entry(workspace)
        elif action == 'chars':
            workspace = 'char'
        elif action == 'moves':
            workspace = 'move'
        action = input('\nNext Action: ').lower()
main()
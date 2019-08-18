import csv
prompt = '''Enter 'chars' to work on characters (the default),
      'moves' to work on moves,
      'sets' to work on move sets,
      'read' to get a list entries in the current workspace,
      'add' to add a new entry to the current workspace,
      'delete' to delete an entry from the current workspace,
   or 'quit' to close the program
(Don't worry about capitalization throughout the course of this program)
        '''
attributes = dict(char = ['Name', 'HP', 'Speed', 'Defense'], move = ['Name', 'Lower Damage', 'Upper Damage', 'Accuracy', 'Status Effect'])
files = dict(char = 'characters.csv', move = 'moves.csv', sets = 'sets.csv')

def print_rows(rows, fieldnames):
    print(*fieldnames, sep='\t\t')
    for row in rows:
        for field in fieldnames:
            print(row[field], end='\t\t')
        print()

def add_entry(workspace):
    with open(files[workspace], 'a', newline='') as csvfile:
        entry = {}
        if workspace == 'sets':
            writer = csv.writer(csvfile)
            entry = [input('Set Name: ').lower()]
            for move in input('Moves: ').lower().split(','):
                entry.append(move.strip())
        else:
            fieldnames = attributes[workspace]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            for field in fieldnames:
                entry[field] = input(field + ': ').title()
        writer.writerow(entry)

def read_file(workspace):
    with open(files[workspace], newline='') as csvfile:
        if workspace == 'sets':
            reader = csv.reader(csvfile)
            for row in reader:
                print(row[0] + ':', row[1:])
        else:
            reader = csv.DictReader(csvfile)
            print_rows(reader, fieldnames = reader.fieldnames)

def delete_entry(workspace):
    entryName = input('What entry would you like to delete? ')
    rows = []
    deleted = []
    with open(files[workspace], newline='') as csvfile:
        if workspace == 'sets':
            reader = csv.reader(csvfile)
            for row in reader:
                if row[0] == entryName.lower():
                    deleted.append(row)
                else:
                    rows.append(row)
        else:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['Name'] == entryName.title():
                    deleted.append(row)
                else:
                    rows.append(row)
            fieldnames = reader.fieldnames
    with open(files[workspace], 'w', newline='') as csvfile:
        if workspace == 'sets':
            writer = csv.writer(csvfile)
        else:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        writer.writerows(rows)
    print('Successfully deleted the following entries:')
    if workspace == 'sets':
        for entry in deleted:
            print(entry)
    else:
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
        elif action == 'sets':
            workspace = 'sets'
        action = input('\nNext Action: ').lower()
main()
import csv
from datetime import datetime
import hashlib
import secrets
import string
from .swen344_db_utils import *

def rebuild_tables():
    drop_sql = """
        DROP SCHEMA IF EXISTS library CASCADE;
    """
    exec_commit(drop_sql)
    exec_sql_file('src/db/library_schema.sql')

'''
Checks to see if the username and password
combination exists in the table. If so, it
generates a secure session key and returns it.
Parameters:
    username(str): A user's username.
    password(str): Hash digest of the password.
Returns:
    (str): A session key.
'''
def login(username, password):
    hashed = hashlib.sha512(password.encode()).hexdigest()
    
    user = exec_get_one("""
        SELECT * FROM users
        WHERE username = %(username)s
        AND password = %(password)s""",
        {'username': username, 'password': hashed})

    if (user != None):
        key = secrets.randbits(32)
        # saves the session key to the user's record
        exec_commit("""
            UPDATE users
            SET session_key = %(key)s
            WHERE username = %(username)s
            AND password = %(password)s""",
            {'key': key, 'username': username, 'password': hashed})

        message = {'Login successful.': str(key)}
        return message

    else:
        return 'Login unsuccessful, incorrect password.'

'''
Returns all of the users in the system.
Returns:
    (list): A list of users (tuples)
'''
def get_all_users():
    return exec_get_all("SELECT * FROM users ORDER BY id ASC")

'''
Returns a user's id given their username.
Parameter: 
    username(str): A username. 
Returns:
    (int): A user's id number in the system.
'''
def get_user_id(username):
    return exec_get_one("SELECT id FROM users WHERE username = %(name)s", {'name': username})[0]
'''
Returns a user's contact info given their user id.
Parameter:
    id(int): A user id.
Returns:
    (str): A user's contact info.
'''
def get_user_contact_info(id):
    return exec_get_one("""
        SELECT contact_info FROM users INNER JOIN checkout 
        ON checkout.user_id = '%(id)s'""", {'id': id})

'''
Returns all of the books in inventory.
Returns:
    (list): A list of books (tuples).
'''
def get_all_books():
    return exec_get_all("""
        SELECT * FROM inventory
    """)

'''
Returns all the books currently checked out by a user.
Parameter:
    id(int): A user id.
Returns:
    (list): A list of books (tuples).
'''
def get_user_books(id):
    return exec_get_all("""
        SELECT checkout.book_id, inventory.title, inventory.author, libraries.library_name,
        check_out_date, due_date, return_date
        FROM checkout
        INNER JOIN inventory ON inventory.book_id = checkout.book_id
        INNER JOIN libraries ON libraries.library_id = checkout.library_id
        WHERE checkout.user_id = %(id)s ORDER BY title ASC""",{'id': id})

'''
Returns all books checked out (sorted by book type / author).
For each book, it says who checked it out and when; return date (or if not returned);
remaining copies.
Returns:
    (list): A list of books (tuples).
'''
def get_checked_out_books():
    return exec_get_all("""
        SELECT inventory.title, users.name, checkout.check_out_date, checkout.return_date,
        inventory.copies FROM users
        INNER JOIN checkout ON checkout.user_id = users.id
        INNER JOIN inventory ON inventory.book_id = checkout.book_id
        ORDER BY inventory.book_type, inventory.author ASC
    """)

'''
Returns all of the nonfiction books in the inventory.
Returns:
    (list): A list of books (tuples).
'''
def get_nonfiction_books():
    return exec_get_all("""
        SELECT * FROM inventory
        WHERE inventory.book_type = 'Non-fiction'
    """)

'''
Returns all of the fiction books in the inventory.
Returns:
    (list): A list of books (tuples).
'''
def get_fiction_books():
    return exec_get_all("""
        SELECT * FROM inventory
        WHERE inventory.book_type = 'Fiction'
    """)

'''
Returns all the books in the inventory that are written by a particular author.
Parameter:
    author(str): Author's name.
Returns:
    (list): A list of books (tuples).
'''
def search_by_author(author):
    return exec_get_all("""
        SELECT * FROM inventory 
        WHERE inventory.author = %(author)s""", {'author': author})

'''
Returns all of the books in the inventory that match the given title.
Parameter:
    title(str): A book title.
Returns:
    (list): A list of books (tuples).
'''
def search_by_title(title):
    return exec_get_all("""
        SELECT * FROM inventory 
        WHERE inventory.title = %(title)s""", {'title': title})

'''
Returns all books that matches multiple search terms.
Parameters:
    type(str): First search term, either fiction or non-fiction.
    string(str): Second search term, either a title or author.
Returns:
    (list): A list of books that matches the search terms.
'''
def search_by_multiple_terms(type, string):
    if (type == 'fiction'):
        if(search_by_author(string) != None):
            return exec_get_all("""
                SELECT * FROM inventory
                WHERE inventory.author = %(author)s
                AND inventory.book_type = 'Fiction'""",
                {'author': string})
        elif(search_by_title(string) != None):
            return exec_get_all("""
                SELECT * FROM inventory
                WHERE inventory.title = %(title)s
                AND inventory.book_type = 'Fiction'""",
                {'title': string})

    elif (type == 'non-fiction'):
        if(search_by_author(string) != None):
            return exec_get_all("""
                SELECT * FROM inventory
                WHERE inventory.author = %(author)s
                AND inventory.book_type = 'Non-fiction'""",
                {'author': string})
        elif(search_by_title(string) != None):
            return exec_get_all("""
                SELECT * FROM inventory
                WHERE inventory.title = %(title)s
                AND inventory.book_type = 'Non-fiction'""",
                {'title': string})

'''
Returns the number of book copies at the specified library given
the library id and book id.
Parameter:
    library_id(int): A library id.
    book_id(int): A book's id.
Returns:
    (int): Number of book copies.
''' 
def get_book_copies(library_id, book_id):
    return exec_get_one("""
        SELECT book_copies FROM library_stock 
        WHERE library_stock.library_id = %(library_id)s
        AND library_stock.book_id = %(book_id)s""",
        {'library_id': library_id, 'book_id': book_id})

'''
Returns the library names that have the book in their inventory.
Parameter:
    book_id(int): A book's id.
Returns:
    (str): A string format of all the libraries.
'''
def get_libraries_with_book(book_id):
    libraries = exec_get_all("""
        SELECT libraries.library_name
        FROM library_stock
        INNER JOIN libraries ON libraries.library_id = library_stock.library_id
        WHERE book_id = %(book_id)s""",
        {'book_id': book_id})

    string = ''
    index = 0
    for library in libraries:
        if (index == 0):
            string = library[0]
            index += 1

        elif (index < libraries.__len__()):
            string = string + ', ' + library[0]
            index += 1

    return string

'''
Returns the corresponding book id given the book title.
Parameter:
    title(str): A book title.
Returns:
    (int): A book's id - 0 if book does not exist in inventory.
'''
def get_book_id(title):
    sql = exec_get_one("""
        SELECT inventory.book_id FROM inventory WHERE inventory.title
        = %(title)s""", {'title': title})
    
    if(sql != None):
        return sql[0]
    else:
        return 0

'''
Creates a new account with the given name and contact info.
Parameters:
    name(str): The user's first and last name.
    contact_info(str): The user's email.
    username(str): Account login username.
    password(str): A password to login.
Returns:
    (str): Message indicating success or not.
'''
def create_account(name, contact_info, username, password):
    exists = exec_get_one("""
        SELECT * FROM users
        WHERE name = %(name)s
        AND username = %(username)s""",
        {'name': name, 'username': username})

    if (exists == None):
        hashed = hashlib.sha512(password.encode()).hexdigest()
    
        exec_commit("""
            INSERT INTO users (name, contact_info, username, password)
            VALUES (%(name)s, %(contact_info)s, %(username)s, %(password)s)""",
            {'name': name, 'contact_info': contact_info, 'username': username, 'password': hashed})
        
        return 'Account created successfully.'

    else:
        return 'Request failed, cannot create account - user already exists.'

'''
Edits a user's contact information.
Parameter:
    user_id(int): A username.
    contact_info(str): The updated contact info.
    key(int): A session key.
Returns:
    (str): A message indicating if account was updated
    or not.
'''
def edit_account(username, contact_info, key):
    user = exec_get_one("""
        SELECT * FROM users
        WHERE username = %(username)s
        AND session_key = %(key)s""",
        {'username': username, 'key': key})

    if (user != None):
        exec_commit("""
            UPDATE users
            SET contact_info = %(info)s
            WHERE username = %(username)s""",
            {'info': contact_info, 'username': username})

        return "User's account info updated successfully."
    
    else:
        return 'Cannot update account info, user does not exist.'

'''
Deletes a user's account given their name.
Parameter:
    name(str): The user's first and last name.
Returns:
    (str): A message indicating whether or not account was deleted.
'''
def delete_account(username, key):
    user = exec_get_one("""
        SELECT * FROM users
        WHERE username = %(username)s
        AND session_key = %(key)s""",
        {'username': username, 'key': key})

    if (user != None):
        exec_commit("""
            DELETE FROM users
            WHERE username = %(username)s
            AND session_key = %(key)s""",
            {'username': username, 'key': key})

        return 'Account successfully deleted.'

    else:
        return 'Cannot remove user, does not exist or wrong session key.'

'''
When books are checked out, they have a pre-assigned maximum lending
time of 2 weeks.
Parameter:
    user_id(int): A user id.
    book_id(int): A book id.
'''
def add_due_date(user_id, book_id):
    exec_commit("""
        UPDATE checkout
        SET due_date = check_out_date +  interval '2 weeks'
        WHERE user_id = %(user_id)s
        AND book_id = %(book_id)s""",
        {'user_id': user_id, 'book_id': book_id})

'''
User checks out a book at a given library. If a user is overdue on a book,
no further checkouts will be allowed.
Parameter:
    library_id(int): A library id.
    title(str): A book title.
    username(str): A username.
    key(int): Session key.
    check_out_date(str): The date the book is checked out.
Returns:
    (tuple): Info regarding the checkout - date checked out, due date etc
'''
def checkout_book(library_id, title, username, key, check_out_date):
    user = exec_get_one("""
        SELECT * FROM users
        WHERE username = %(username)s
        AND session_key = %(key)s""",
        {'username': username, 'key': key})

    if (user == None):
        return 'No authentication, cannot checkout book.'

    user_id = get_user_id(username)

    # check if there's any overdue books, if there are, user cannot make further checkouts
    due_dates = exec_get_all("""
        SELECT due_date FROM checkout
        WHERE user_id = %(user_id)s
        AND due_date IS NOT NULL""",
        {'user_id': user_id})

    overdue = 0
    for dates in due_dates:
        if (datetime.strptime(check_out_date, '%Y-%m-%d').date() > dates[0]):
            overdue += 1
            break
    
    if (overdue == 1):
        raise Exception("Cannot checkout book because user has an overdue book")

    else:
        book_id = get_book_id(title)

        # updates master inventory count
        exec_commit("""
            UPDATE inventory SET copies = (copies - 1)
            WHERE book_id = %(book_id)s""", {'book_id': book_id})

        # updates library inventory count
        exec_commit("""
            UPDATE library_stock SET book_copies = (book_copies - 1)
            WHERE book_id = %(book_id)s
            AND library_stock.library_id = %(library_id)s""",
            {'book_id': book_id, 'library_id': library_id})

        exec_commit("""
            INSERT INTO checkout (library_id, book_id, user_id, check_out_date)
            VALUES (%(library_id)s, %(book_id)s, %(user_id)s, %(check_out_date)s)""",
            {'library_id': library_id, 'book_id': book_id, 'user_id': user_id, 'check_out_date': check_out_date})

        # add maximum lending time of 2 weeks
        add_due_date(user_id, book_id)

        return title + ' successfully checked out.'

'''
User returns a book at a given library. Also calculates the late
fees if the book was overdue.
Parameter:
    library_id(int): A library id.
    book_id(int): A book id.
    user_id(int): A user id.
    return_date(str): The date the book is returned.
Returns:
    (tuple): The full checkout history - date checked out, date returned etc
'''
def return_book(library_id, book_id, user_id, return_date):
    # updates master inventory
    exec_commit("""
        UPDATE inventory SET copies = (copies + 1)
        WHERE book_id = %(book_id)s""", {'book_id': book_id})

    # updates library inventory
    exec_commit("""
        UPDATE library_stock SET book_copies = (book_copies + 1)
        WHERE book_id = %(book_id)s
        AND library_stock.library_id = %(library_id)s""",
        {'book_id': book_id, 'library_id': library_id})
    
    # calculate any late fees
    days_late, fee = apply_late_fees(user_id, book_id, return_date)
    if(fee > 0.0):
        print('\nYou returned your book', int(days_late), 'days late. You have a late fee of $', fee)

    # updates table to show return date & sets previous due date to null
    exec_commit("""
        UPDATE checkout SET return_date = %(return_date)s,
        due_date = NULL
        WHERE book_id = %(book_id)s
        AND user_id = %(user_id)s
        AND checkout.library_id = %(library_id)s""",
        {'return_date': return_date, 'book_id': book_id, 'user_id': user_id, 'library_id': library_id})

    # return
    sql = exec_get_all("""
            SELECT * FROM checkout
            WHERE user_id = %(user_id)s
            AND book_id = %(book_id)s""",
            {'user_id': user_id, 'book_id': book_id})[0]

    return sql

'''
User reserves a book, only reserves successfully if there are no copies
of the book left at the specified library.
Parameters:
    library_id(int): A library id.
    reserve_book_id(int): A book id.
    user_id(int): A user id.
'''
def reserve_book(library_id, reserve_book_id, user_id):
    book_copies = get_book_copies(library_id, reserve_book_id)
    if (book_copies[0] == 0):
        exec_commit("""
            INSERT INTO reserve(library_id, reserve_book_id, user_id)
            VALUES (%(library_id)s, %(reserve_book_id)s, %(user_id)s)""",
            {'library_id': library_id, 'reserve_book_id': reserve_book_id, 'user_id': user_id})
    else:
        raise Exception("copies of the book are still available")

'''
Loads the set of information on books from a file and adds it to the database.
Parameter:
    filename(str): Csv file with test data.
'''
def insert_data_from_csv(filename):
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)

        for record in csv_reader:
            title = record[0]
            author = record[1]
            summary = record[2]
            book_type = record[3]
            copies = record[5]

            exec_commit("""
                INSERT INTO inventory(title, book_type, author, publish_date, summary, copies)
                VALUES (%(title)s, %(book_type)s, %(author)s, NULL, %(summary)s, %(copies)s)""",
                {'title': title, 'book_type': book_type, 'author': author, 'summary': summary, 'copies': copies})

'''
Checks to see if the book already exists in the inventory. If there is, simply
updates the number of copies in the inventory. If not, it adds the new book.
Parameters:
    title(str): Title of a book.
    book_type(str): Genre of a book.
    author(str): Author's name.
    copies(int): Number of copies of the book.
Returns:
    (int): Newly added book_id if it is not already in the inventory.
'''
def add_new_book(title, book_type, author, add_copies):
    # first check to see if the same book already exists in inventory
    book_id = get_book_id(title)

    # if there is, just update the number of copies
    if(book_id != 0):
            sql = f"""
            UPDATE inventory SET copies = (copies + {add_copies})
            WHERE book_id = {book_id}"""
            exec_commit(sql)

    # if not, just add the new book to the inventory
    else:
        exec_commit("""
            INSERT INTO inventory(title, book_type, author, copies)
            VALUES (%(title)s, %(book_type)s, %(author)s, %(add_copies)s)""",
            {'title': title, 'book_type': book_type, 'author': author, 'add_copies': add_copies})

    return get_book_id(title)

'''
Adds a new book to the specified library's inventory if it is not alrady there,
otherwise it updates the book count with the given additional copies.
Parameters:
    library_id(int): A library's id.
    book_id(int): A book's id.
    book_copies(int): Number of copies of the book.
'''
def add_to_library(library_id, book_id, book_copies):
    # first check to see if the book already exists in the library's system
    copies = get_book_copies(library_id, book_id)

    # if there is, just update the number of copies
    if(copies != None):
            sql = f"""
            UPDATE library_stock SET book_copies = (book_copies + {book_copies})
            WHERE book_id = {book_id}
            AND library_id = {library_id}"""
            exec_commit(sql)
    
    # if not, add it into the system
    else:
        exec_commit("""
            INSERT INTO library_stock(library_id, book_id, book_copies)
            VALUES (%(library_id)s, %(book_id)s, %(book_copies)s)""",
            {'library_id': library_id, 'book_id': book_id, 'book_copies': book_copies})

'''
Returns a listing of a user's lending history including their late history.
Parameter:
    user_id(int): A user id.
Returns:
    (list): A list of the user's lending history.
'''
def get_user_history(user_id):
    return exec_get_all("""
        SELECT inventory.title, check_out_date, due_date, return_date
        FROM checkout
        INNER JOIN inventory ON inventory.book_id = checkout.book_id
        WHERE user_id = %(user_id)s""",
        {'user_id': user_id})

'''
As a librarian, this returns a comprehensive list of all late books and histories
at the specified library.
Parameter:
    library_id(int): A library's id.
Returns:
    (list): All checkout histories including late books.
'''
def get_all_histories(library_id):
    #NEEDS TESTING
    return exec_get_all("""
        SELECT inventory.title, users.name, check_out_date, due_date, return_date
        FROM checkout
        INNER JOIN inventory ON inventory.book_id = checkout.book_id
        INNER JOIN users ON users.id = checkout.user_id
        WHERE library_id = %(library_id)s""",
        {'library_id': library_id})

'''
Runs a report listing all books in all libraries, organized by library location
and book title with the count of books at each location.
Returns:
    (list): A list of all books in all libraries (tuples).
'''
def report_on_all_libraries():
    books = exec_get_all("""
        SELECT libraries.library_name, inventory.title
        FROM library_stock
        INNER JOIN inventory ON inventory.book_id = library_stock.book_id
        INNER JOIN libraries ON libraries.library_id = library_stock.library_id
        ORDER BY libraries.library_name, inventory.title ASC
    """)

    for book in books:
        print(book)

    print('Number of books at each location:')
    print('Fairport:', total_books_at_library(2))
    print('Henrietta:', total_books_at_library(3))
    print('Penfield:', total_books_at_library(1))
    print('Pittsford:', total_books_at_library(4))

    return books

'''
Calculates the total number of books at a specified library,
adding up all the copies of each book there.
Parameter:
    library_id(int): A library's id.
Returns:
    (int): Total number of books at this library.
'''
def total_books_at_library(library_id):
    count = 0
    copies = exec_get_all("""
        SELECT book_copies
        FROM library_stock
        WHERE library_id = %(library_id)s""",
        {'library_id': library_id})

    for copy in copies:
        count += copy[0]

    return count

'''
Calculates the late-fee charge if a book is past due.
$0.25 for the first week, and $2.00 per day after that.
Parameters:
    user_id(int): A user's id.
    book_id(int): A book id.
    return_date(str): Date the book is returned.
Returns:
    (int): Number of days late.
    (float): Late fee.
'''
def apply_late_fees(user_id, book_id, return_date):
    fee = 0.0
    due_date = exec_get_one("""
        SELECT due_date
        FROM checkout
        WHERE user_id = %(user_id)s
        AND book_id = %(book_id)s""",
        {'user_id': user_id, 'book_id': book_id})[0]
    
    if (datetime.strptime(return_date, '%Y-%m-%d').date() > due_date):
        days_late = datetime.strptime(return_date, '%Y-%m-%d').date() - due_date
        days_late = float(str(days_late).split(' ')[0])
        
        if (days_late <= 6):
            fee = days_late * 0.25
        else:
            fee = 6 * 0.25
            fee += 2*(days_late - 6)
    
        sql = f"""
            UPDATE checkout
            SET late_fees = {fee}
            WHERE user_id = {user_id}
            AND book_id = {book_id}"""
        exec_commit(sql)
        
        return days_late, fee

    return 0, fee

'''
Presents a table listing of each book and who has checked it out.
'''
def checkout_table():
    books = exec_get_all("""
        SELECT inventory.title, inventory.author, users.name,
        check_out_date, return_date, late_fees
        FROM checkout
        INNER JOIN users ON users.id = checkout.user_id
        INNER JOIN inventory ON inventory.book_id = checkout.book_id
    """)

    output = '%-45s  %-18s  %-15s  %-15s  %-10s' % ('book', 'name', 'check_out_date', 'returned_date', 'late_fees')
    print(output)
    print('-' * 110)

    for book in books:
        title_author = book[0] + ' by ' + book[1]
        name = book[2]
        checkout_date = book[3]
        return_date = book[4]
        late_fees = book[5]

        output = '%-45s  %-18s  %-15s  %-15s  %8s' % (title_author, name, checkout_date, return_date, late_fees)
        print(output)

'''
Generates a report that lists each book that has been checked out,
the number of days for which it was checked out, and lastly prints
the average number of days it takes for a book to be returns.
'''
def generate_report():
    average = 0

    books = exec_get_all("""
        SELECT inventory.title, users.name, check_out_date, return_date
        FROM checkout
        INNER JOIN users ON users.id = checkout.user_id
        INNER JOIN inventory ON inventory.book_id = checkout.book_id
    """)

    output = '%-25s  %-20s  %-15s  %-15s  %-10s' % ('Title', 'User', 'Checkout', 'Return', 'Days borrowed')
    print(output)

    for book in books:
        title = book[0]
        name = book[1]
        checkout_date = book[2]
        return_date = book[3]

        if (return_date != None):
            days_borrowed = return_date - checkout_date
            days_borrowed = int(str(days_borrowed).split(' ')[0])
            average += days_borrowed
        else:
            days_borrowed = None

        output = '%-25s  %-20s  %-15s  %-15s  %-10s' % (title, name, checkout_date, return_date, days_borrowed)
        print(output)

    average = average / books.__len__()
    print('\nAverage return time = ', round(average, 2), 'days')

def main():
    rebuild_tables()

main()
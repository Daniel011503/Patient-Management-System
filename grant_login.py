import sys
import getpass
import psycopg2

# Usage: python grant_login.py <username> <password>
# Example: python grant_login.py myuser mypassword

def main():
    if len(sys.argv) != 3:
        print("Usage: python grant_login.py <username> <password>")
        sys.exit(1)
    username = sys.argv[1]
    password = sys.argv[2]

    # Prompt for postgres admin password
    admin_password = getpass.getpass("Enter postgres admin password: ")

    try:
        conn = psycopg2.connect(dbname="postgres", user="postgres", password=admin_password, host="localhost", port=5432)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"ALTER ROLE {username} WITH LOGIN;")
        cur.execute(f"ALTER USER {username} WITH PASSWORD %s;", (password,))
        print(f"✅ Login privilege and password set for user '{username}'.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

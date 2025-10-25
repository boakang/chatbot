from database import DatabaseHelper

db = DatabaseHelper()

# Test admin key
print("Testing admin key...")
result = db.verify_admin_key("123222")
print(f"Admin key valid: {result}")

# Test get pending tickets
print("\nGetting pending tickets...")
tickets = db.get_pending_tickets()
print(f"Found {len(tickets)} pending tickets")
for ticket in tickets:
    print(f"  - Ticket #{ticket['ticket_id']}: {ticket['content']}")

print("\n✅ Database connection successful!")
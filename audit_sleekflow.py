from sleekflow_service import SleekFlowService


print("=" * 60)
print("SLEEKFLOW API AUDIT")
print("=" * 60)


service = SleekFlowService()


# =========================================================
# CONTACTS
# =========================================================

print("\n===== CONTACTS =====")

try:
    contacts = service.get_contacts()

    print(
        "Response type:",
        type(contacts).__name__
    )

    if isinstance(contacts, dict):
        print(
            "Response keys:",
            list(contacts.keys())
        )

    elif isinstance(contacts, list):
        print(
            "Jumlah records:",
            len(contacts)
        )

    print("\nSample response:")

    print(contacts)

except Exception as e:

    print(
        "ERROR CONTACTS:",
        repr(e)
    )


# =========================================================
# TICKETS
# =========================================================

print("\n===== TICKETS =====")

try:
    tickets = service.get_tickets()

    print(
        "Response type:",
        type(tickets).__name__
    )

    if isinstance(tickets, dict):
        print(
            "Response keys:",
            list(tickets.keys())
        )

    elif isinstance(tickets, list):
        print(
            "Jumlah records:",
            len(tickets)
        )

    print("\nSample response:")

    print(tickets)

except Exception as e:

    print(
        "ERROR TICKETS:",
        repr(e)
    )


print("\n" + "=" * 60)
print("AUDIT SELESAI")
print("=" * 60)

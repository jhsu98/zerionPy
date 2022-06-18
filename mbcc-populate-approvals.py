from zerionPy import ifb
from pprint import pprint

server = "masterbuilderssolutions"
client_key = "8ed634af03a0a2186a9e498945394f43d6878a03"
client_secret = "dacdbe5dcb4a522a3e2b1aa15a82ee1fcd90c07e"

profile_id = 490141
page_id = 3780454

api = ifb.IFB(server, client_key, client_secret, 8, 'us', True, False)

# print(api.deleteElements(profile_id, page_id, { 'fields': 'sort_order(>="2")'}))

for n in range(1,101):
    body = {
        'label': f'Attendee {n}',
        'name': f'attendee_{n}',
        'data_type': 7,
        'optionlist_id': 4941145,
        'dynamic_label': f'customer_contact_approvals.attendees.split("\\n")[{n-1}].split(",")[0]',
        'condition_value': f'customer_contact_approvals.attendees_count >= {n}'
    }

    print(api.postElements(profile_id, page_id, body))
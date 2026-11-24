# Orders request data

The generator uses only the Python standard library. The scoped OpenAPI 3.1 document uses JSON syntax, a YAML subset. From the repository root run

~~~powershell
python sqe/generate_orders_cases.py
python sqe/generate_orders_cases.py --revision
python sqe/generate_orders_cases.py --check
python sqe/generate_orders_cases.py --revision --check
~~~

Each JSONL row identifies a single field variation. For GET path cases the base is `sqe-orders/orders/SQE02`. Query cases vary the optional canceled-position filter on that order. For POST cases the base body is `{"send_email":false}`. The test runner supplies a separate seeded order per body case. An omitted field is absent from the serialized input. `valid` classifies the input against the client contract. A syntactically valid identifier can still refer to an absent resource.

| Revision input | Original triple | Revised triple |
| --- | --- | --- |
| Maximum order code length, characters | 15, 16, 17 | 11, 12, 13 |
| Maximum retained fee, EUR | 19.99, 20.00, 20.01 | 24.99, 25.00, 25.01 |

The two edits are in [revision.json](revision.json). The revised dataset models a hypothetical profile. Run live tests with the original EUR 20.00 fixtures. Boolean and nullable fields, resource existence, and the character alphabet have discrete partitions. The comment action declares no length limit. The fee capacity triple also exceeds the fixture cap, so the two rejection causes overlap above the storage maximum. Decimal scale is exercised around two places.

[Original dataset](orders.jsonl) · [Revised dataset](orders-revised.jsonl) · [OpenAPI contract](../openapi.yaml) · [Pinned actions](../../src/pretix/api/views/order.py)

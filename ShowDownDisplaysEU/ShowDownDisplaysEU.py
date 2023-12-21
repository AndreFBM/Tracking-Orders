import pyodbc
import requests
import xml.etree.ElementTree as ET
import base64

# Database Credentials (Replace with your credentials)
server = 'YOUR_SERVER'
database = 'YOUR_DATABASE'
username = 'YOUR_USERNAME'
password = 'YOUR_PASSWORD'
conn_str = f"Driver={{SQL Server}};Server={server};Database={database};UID={username};PWD={password}"
cnxn = pyodbc.connect(conn_str)

# API credentials (Replace with your credentials)
api_username = 'YOUR_API_USERNAME'
api_password = 'YOUR_API_PASSWORD'

# Encode API credentials
credentials = f'{api_username}:{api_password}'
encoded_credentials = base64.b64encode(credentials.encode()).decode()

cursor = cnxn.cursor()

# Execute the SELECT query
cursor.execute(
    "SELECT DISTINCT StockOrderID FROM DW_360Imprimir.op.stock_orderRequest WHERE StockSupplier = 'ShowdownDisplayEU' AND StockTrackingCode is null")
stock_order_ids = cursor.fetchall()

# API details
url = "https://shop.showdowndisplays.eu/api/order/status"
headers = {
    "Authorization": "Basic " + encoded_credentials,
}
body_template = """
<order xmlns="http://www.jansen-display.cz/partner/order">
    <user>
        <email>YOUR_EMAIL</email>
        <password>YOUR_PASSWORD</password>
    </user>
   <order_id>{}</order_id>
</order>
"""

# Define the XML namespace
ns = {'ns': 'http://www.jansen-display.cz/partner/order'}

for order_id in stock_order_ids:
    # Update the body with the current order ID
    body = body_template.format(order_id[0])
    response = requests.get(url, headers=headers, data=body)
    print("Processing order_id:", order_id[0])

    # Parse the response
    root = ET.fromstring(response.content)

    # Find the tracking_numbers element using the namespace
    tracking_numbers_element = root.find('.//ns:tracking_numbers', ns)
    if tracking_numbers_element is not None:
        tracking_number = tracking_numbers_element.find('.//ns:tracking_number', ns)

        # Check if the tracking_number is not None and has text content
        if tracking_number is not None and tracking_number.text:
            print("Tracking Number Found:", tracking_number.text)

            # Update the database with the tracking number
            update_query = "UPDATE DW_360Imprimir.op.stock_orderRequest SET StockTrackingCode = ? WHERE StockOrderID = ? AND StockSupplier = 'ShowdownDisplayEU'"
            cursor.execute(update_query, (tracking_number.text, order_id[0]))
            cnxn.commit()
            print("Tracking Code Updated for order_id:", order_id[0])
        else:
            print("No tracking number found for order_id", order_id[0])
    else:
        print("No tracking numbers element found for order_id", order_id[0])

# Close the database connection
cursor.close()
cnxn.close()

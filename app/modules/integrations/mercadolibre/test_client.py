from app.modules.integrations.mercadolibre.client import MercadoLibreClient

# ⚠️ TOKEN DEV - luego va a .env
ML_ACCESS_TOKEN = "PEGA_ACA_TU_ACCESS_TOKEN"


def run_test():
    client = MercadoLibreClient(ML_ACCESS_TOKEN)

    user = client.get_current_user()
    print("USER:")
    print(user)

    user_id = user["id"]

    items = client.get_item_ids(user_id)
    print("\nITEM IDS:")
    print(items["results"][:5])

    if items["results"]:
        first_item_id = items["results"][0]
        item_detail = client.get_item_detail(first_item_id)

        print("\nITEM DETAIL:")
        print({
            "id": item_detail.get("id"),
            "title": item_detail.get("title"),
            "status": item_detail.get("status"),
        })


if __name__ == "__main__":
    run_test()

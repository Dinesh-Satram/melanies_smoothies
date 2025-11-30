# Import python packages
import streamlit as st
from snowflake.snowpark.functions import col
import requests
import pandas as pd

# ---------------- HEADER ----------------
st.title(":cup_with_straw: Customize Your Smoothie! :cup_with_straw:")
st.write(
    """Choose the fruits you want in your custom Smoothie!
    """
)

name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be:", name_on_order)

# ---------------- SNOWFLAKE CONNECTION ----------------
cnx = st.connection("snowflake")
session = cnx.session()

# Get FRUIT_NAME and SEARCH_ON from the table
fruit_df = (
    session.table("smoothies.public.fruit_options")
    .select(col("FRUIT_NAME"), col("SEARCH_ON"))
    .order_by(col("FRUIT_NAME"))
)

pd_df = fruit_df.to_pandas()

# ---------------- MULTISELECT ----------------
ingredients_list = st.multiselect(
    "Choose upto 5 ingredients:",
    pd_df["FRUIT_NAME"].tolist(),   # list of names only
    max_selections=5,
)

# ---------------- MAIN LOGIC ----------------
if ingredients_list:
    # 1️⃣ Build one clean string for inserting into ORDERS (no trailing spaces)
    ingredients_string = " ".join(f.strip() for f in ingredients_list)

    # For each chosen fruit, look up SEARCH_ON and call API
    for fruit_chosen in ingredients_list:
        # Look up the search term
        search_on = pd_df.loc[
            pd_df["FRUIT_NAME"] == fruit_chosen, "SEARCH_ON"
        ].iloc[0]

        st.write("The search value for ", fruit_chosen, " is ", search_on, ".")

        st.subheader(f"{fruit_chosen} Nutrition Information")

        # 2️⃣ Call SmoothieFroot API with basic error-handling
        url = f"https://my.smoothiefroot.com/api/fruit/{search_on}"

        try:
            smoothiefroot_response = requests.get(url, timeout=10)

            if smoothiefroot_response.status_code == 404:
                st.warning(
                    f"No nutrition data found in SmoothieFroot for '{search_on}'."
                )
                continue  # skip to next fruit

            smoothiefroot_response.raise_for_status()

            # Show the JSON response as a table
            api_df = pd.json_normalize(smoothiefroot_response.json())
            st.dataframe(api_df, use_container_width=True)

        except requests.RequestException as e:
            st.error(f"Error calling SmoothieFroot for '{search_on}': {e}")
            continue  # don’t break the whole app

    st.write(ingredients_string)

    # Insert the order into ORDERS table
    my_insert_stmt = f"""
        insert into smoothies.public.orders(INGREDIENTS, NAME_ON_ORDER)
        values ('{ingredients_string}', '{name_on_order}')
    """

    time_to_insert = st.button("Submit Order")

    if time_to_insert:
        session.sql(my_insert_stmt).collect()
        st.success("Your Smoothie is ordered! " + name_on_order, icon="✅")

    st.write(my_insert_stmt)

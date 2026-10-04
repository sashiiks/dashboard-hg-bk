import streamlit as st


def apply_dashboard_style():
    st.markdown(
        """
        <style>

        /* ================================
           GLOBAL
        ================================= */

        .stApp {
            background-color: #F7F6FA;
        }

        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        h1, h2, h3 {
            color: #30303A;
        }

        p, label, .stCaption {
            color: #777784;
        }


        /* ================================
           SIDEBAR
        ================================= */

        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #ECEAF2;
        }


        /* ================================
           METRIC
        ================================= */

        [data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #ECEAF2;
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 2px 10px rgba(60, 55, 80, 0.04);
        }

        [data-testid="stMetricLabel"] {
            color: #777784;
            font-size: 0.85rem;
        }

        [data-testid="stMetricValue"] {
            color: #30303A;
            font-weight: 700;
        }


        /* ================================
           DATAFRAME
        ================================= */

        [data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid #ECEAF2;
        }


        /* ================================
           DIVIDER
        ================================= */

        hr {
            border: none;
            border-top: 1px solid #E9E7EF;
            margin: 1.5rem 0;
        }


        /* ================================
           INFO BOX
        ================================= */

        [data-testid="stAlert"] {
            border-radius: 12px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

import streamlit as st

from version import VERSION, BUILD, ENGINE


def render_footer():

    st.markdown("---")

    st.caption(

        f"SharpStack {VERSION} • Build {BUILD} • {ENGINE}"

    )

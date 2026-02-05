import streamlit as st 
import webbrowser as wb
import subprocess as sb
st.markdown("""
    <style>
    .title  
    {
        color: blue;
        text-align: center;
        font-size: 70px;
        font-weight: bold;
        width: 100%;
        padding: 0.75rem;
        background-color: white;
        border: none;
        border-radius: 10px;
        font-size: 3rem;
        cursor: pointer;
        argin-top: 1rem;
        transition: background-color 0.3s ease;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title"><b>facebook</b></div><br><br>', unsafe_allow_html=True)
with st.form(key="st.form_submit_button()"):
 name=st.text_input("USERNAME",placeholder="Enter username or phonenumber")
 password=st.text_input("PASSWORD",type="password",placeholder="Enter password")
 button=st.form_submit_button("Login")
if button:
    if name == 'cedrick' and password =='12345':
       st.success(f"Thank you {name} your login process is successfully")
       wb.open("https://www.facebook.com")
    else:
        st.write("check your cridentials 🤷‍♂️")
else:
       st.markdown('<a href="http://localhost:8501">Create new account </a></div>',unsafe_allow_html=True)
      

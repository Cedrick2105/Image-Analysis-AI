import streamlit as st
import random
import time
import pandas as pd # Needed for the line chart

# --- Configuration ---
MIN_MULTIPLIER = 1.01
MAX_MULTIPLIER = 100.0 

# --- Session State Initialization ---
# Core game state
if 'balance' not in st.session_state:
    st.session_state.balance = 100.00
if 'game_running' not in st.session_state:
    st.session_state.game_running = False
if 'current_multiplier' not in st.session_state:
    st.session_state.current_multiplier = 1.00
if 'bet_amount' not in st.session_state:
    st.session_state.bet_amount = 0.00
if 'can_cashout' not in st.session_state:
    st.session_state.can_cashout = False
if 'last_crashed' not in st.session_state:
    st.session_state.last_crashed = []
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'home'

# Admin controlled state
if 'next_crash_point' not in st.session_state:
    st.session_state.next_crash_point = random.uniform(1.01, 10.0) 
if 'growth_factor' not in st.session_state:
    st.session_state.growth_factor = 0.5


# --- Navigation Functions ---
def set_view(view_name):
    st.session_state.current_view = view_name

# --- Wallet Functions (Updated for Phone/PIN) ---

def handle_deposit(amount, phone_number, pin):
    # --- SIMULATION ONLY ---
    if not phone_number or not pin:
        st.error("Please enter both Phone Number and PIN.")
        return
    if amount <= 0:
        st.error("Deposit amount must be greater than zero.")
        return
    # --- SIMULATION COMPLETE ---
    
    st.session_state.balance += amount
    st.toast(f"✅ Deposit of ${amount:.2f} successful on {phone_number}!", icon="💵")
    
    # Hide the form after success
    st.session_state.show_deposit_form = False
    st.experimental_rerun()


def handle_withdrawal(amount, phone_number):
    # --- SIMULATION ONLY ---
    if not phone_number:
        st.error("Please enter the Phone Number for withdrawal.")
        return
    if amount <= 0 or amount > st.session_state.balance:
        st.error("Invalid withdrawal amount.")
        return
    # --- SIMULATION COMPLETE ---

    st.session_state.balance -= amount
    st.toast(f"🏦 Withdrawal of ${amount:.2f} sent to {phone_number}.", icon="✅")
    
    # Hide the form after success
    st.session_state.show_withdrawal_form = False
    st.experimental_rerun()


# --- Game Functions (Same as before) ---
def generate_crash_point_random():
    r = random.random()
    if r < 0.2: 
        return random.uniform(1.01, 1.50)
    elif r < 0.8: 
        return random.uniform(1.51, 10.00)
    else: 
        return random.uniform(10.01, MAX_MULTIPLIER)

def start_game(bet):
    if st.session_state.game_running:
        st.error("Game is already running.")
        return
    if bet <= 0 or bet > st.session_state.balance:
        st.error("Invalid bet amount or insufficient funds.")
        return
    
    # 1. Deduct bet and set state
    st.session_state.balance -= bet
    st.session_state.bet_amount = bet
    st.session_state.game_running = True
    st.session_state.can_cashout = True
    st.session_state.current_multiplier = 1.00
    
    if st.session_state.next_crash_point:
        st.session_state.crash_point = st.session_state.next_crash_point
        st.session_state.next_crash_point = generate_crash_point_random() 
    else:
        st.session_state.crash_point = generate_crash_point_random()

    st.toast(f"Bet of ${bet:.2f} placed! Round started.", icon="🚀")

def cashout():
    if not st.session_state.can_cashout:
        st.warning("Cannot cash out now.")
        return
    
    payout = st.session_state.bet_amount * st.session_state.current_multiplier
    st.session_state.balance += payout
    st.toast(f"Cashed out at {st.session_state.current_multiplier:.2f}x! Won ${payout:.2f}.", icon="💰")
    
    # End the round
    st.session_state.game_running = False
    st.session_state.can_cashout = False
    st.session_state.last_crashed.insert(0, st.session_state.current_multiplier)
    if len(st.session_state.last_crashed) > 10:
        st.session_state.last_crashed.pop()


# --- Main App Views ---

def home_view():
    st.title("💸 Welcome to the Aviator Simulator")
    st.markdown("---")
    st.header("Select Your Role")

    col1, col2 = st.columns(2)
    
    with col1:
        st.button("🙋 User for Betting", on_click=set_view, args=('user_panel',), use_container_width=True, type="primary")
    
    with col2:
        st.button("⚙️ Admin Panel", on_click=set_view, args=('admin_panel',), use_container_width=True)
    st.markdown("---")


def admin_panel_view():
    st.title("⚙️ Admin Control Panel")
    st.button("🏠 Back to Home", on_click=set_view, args=('home',))
    st.markdown("---")
    
    st.session_state.next_crash_point = st.number_input(
        "Set Next Crash Multiplier (Admin Only)", 
        min_value=MIN_MULTIPLIER, 
        max_value=MAX_MULTIPLIER, 
        value=st.session_state.next_crash_point, 
        step=0.01,
        format="%.2f"
    )
    
    st.session_state.growth_factor = st.slider(
        "Multiplier Growth Factor (Game Speed)", 
        min_value=0.1, max_value=2.0, 
        value=st.session_state.growth_factor, 
        step=0.1
    )
    st.markdown("---")
    st.text(f"Is Game Running? {st.session_state.game_running}")
    st.markdown("Last Crashes: " + " ".join([f"**{m:.2f}x**" for m in st.session_state.last_crashed]))


def user_panel_view():
    st.title("🙋 User Betting Panel")
    st.button("🏠 Back to Home", on_click=set_view, args=('home',))
    st.markdown("---")
    
    # --- Sidebar for Wallet/Admin Controls ---
    with st.sidebar:
        st.header("💳 Mobile Money Wallet")
        st.metric(label="Current Balance", value=f"${st.session_state.balance:.2f}")

        # Deposit Form Button
        if st.button("💰 Deposit via Mobile Money", use_container_width=True):
            st.session_state.show_deposit_form = True
        
        # Withdrawal Form Button
        if st.button("🏦 Withdraw Funds", use_container_width=True):
            st.session_state.show_withdrawal_form = True

        st.markdown("---")
        st.info(f"Next Crash Point (Set by Admin): {st.session_state.next_crash_point:.2f}x")

    # --- Deposit Modal/Form ---
    if st.session_state.get('show_deposit_form', False):
        with st.form("deposit_form"):
            st.subheader("💵 Simulated Deposit")
            dep_phone = st.text_input("Mobile Phone Number (e.g., 078xxxxxxx)", value="078xxxxxxx")
            dep_pin = st.text_input("Mobile Money PIN (Simulated)", type="password") # Real apps would never ask for this
            dep_amount = st.number_input("Deposit Amount ($)", min_value=1.00, value=50.00, step=1.00)
            
            submitted = st.form_submit_button("Confirm Deposit", type="primary")
            if submitted:
                handle_deposit(dep_amount, dep_phone, dep_pin)

    # --- Withdrawal Modal/Form ---
    if st.session_state.get('show_withdrawal_form', False):
        with st.form("withdrawal_form"):
            st.subheader("🏦 Simulated Withdrawal")
            wdraw_phone = st.text_input("Mobile Phone Number to Receive Funds", value="078xxxxxxx")
            wdraw_amount = st.number_input("Withdrawal Amount ($)", min_value=1.00, max_value=st.session_state.balance, value=10.00, step=1.00)
            
            submitted = st.form_submit_button("Confirm Withdrawal", type="primary")
            if submitted:
                handle_withdrawal(wdraw_amount, wdraw_phone)
    
    # --- Main Betting Interface ---
    
    col_history, col_bet = st.columns([2, 1])

    with col_bet:
        # Display the balance again for clarity
        st.metric(label="Account Balance", value=f"${st.session_state.balance:.2f}")
        
        bet_input = st.number_input("Enter Bet Amount ($)", min_value=1.00, max_value=st.session_state.balance, step=1.00, value=5.00, key='bet_input', disabled=st.session_state.game_running)
        
        st.button("🚀 Place Bet", on_click=start_game, args=(bet_input,), disabled=st.session_state.game_running, type="secondary")
        
        if st.session_state.game_running:
            st.button(f"💰 Cash Out at {st.session_state.current_multiplier:.2f}x", on_click=cashout, disabled=not st.session_state.can_cashout, type="primary", use_container_width=True)

    with col_history:
        st.subheader("Last 10 Crash Points")
        st.markdown(" ".join([f"**{m:.2f}x**" for m in st.session_state.last_crashed]))

    st.markdown("---")
    
    # --- Game Logic Loop (Simulated) ---

    if st.session_state.game_running:
        
        col_chart, col_status = st.columns([3, 1])
        chart_placeholder = col_chart.empty()
        status_placeholder = col_status.empty()
        plane_placeholder = col_chart.empty()
        sound_placeholder = col_chart.empty()
        
        # We need a DataFrame for the line chart
        multiplier_data = pd.DataFrame({'Multiplier': []})
        
        start_time = time.time()
        
        plane_placeholder.markdown("🛫 **Plane Taking Off...** (Sound: **VROOOMMM**)", unsafe_allow_html=True)
        sound_placeholder.markdown("🔊 **Engine Roar**", unsafe_allow_html=True)
        
        while st.session_state.game_running and st.session_state.current_multiplier < st.session_state.crash_point:
            
            elapsed_time = time.time() - start_time
            
            # Use the admin-controlled growth_factor
            st.session_state.current_multiplier = 1.0 + elapsed_time * st.session_state.growth_factor
            
            # --- Visual Updates ---
            multiplier_data.loc[len(multiplier_data)] = st.session_state.current_multiplier
            
            # Draw the graph showing the plane's ascent
            chart_placeholder.line_chart(multiplier_data, use_container_width=True)
            
            # Update the large multiplier display
            status_placeholder.markdown(f"## **<p style='color: green;'>{st.session_state.current_multiplier:.2f}x</p>**", unsafe_allow_html=True)
            plane_placeholder.markdown(f"✈️ **Flying at Altitude: {st.session_state.current_multiplier:.2f}x** (Sound: **Woooooosh**)", unsafe_allow_html=True)
            
            time.sleep(0.05) 
            
            if st.session_state.current_multiplier >= st.session_state.crash_point and st.session_state.game_running:
                break

        # --- Crash Event ---
        
        if st.session_state.game_running:
            # Final update to the crash point
            st.session_state.current_multiplier = st.session_state.crash_point
            multiplier_data.loc[len(multiplier_data)] = st.session_state.current_multiplier
            chart_placeholder.line_chart(multiplier_data, use_container_width=True)
            
            st.error(f"🔴 CRASHED at **{st.session_state.crash_point:.2f}x**")
            status_placeholder.markdown(f"## **<p style='color: red;'>{st.session_state.crash_point:.2f}x</p>**", unsafe_allow_html=True)
            plane_placeholder.markdown("💥 **Plane Exploded!** (Sound: **BOOOM!**)", unsafe_allow_html=True)
            sound_placeholder.empty()
            st.toast(f"You lost ${st.session_state.bet_amount:.2f}", icon="🔥")
            
            st.warning(f"You did not cash out. Lost ${st.session_state.bet_amount:.2f}")
            
            # End the round
            st.session_state.game_running = False
            st.session_state.can_cashout = False
            st.session_state.last_crashed.insert(0, st.session_state.crash_point)
            if len(st.session_state.last_crashed) > 10:
                st.session_state.last_crashed.pop()
        
        st.experimental_rerun() 

    else:
        st.info(f"Next round will crash at: **{st.session_state.next_crash_point:.2f}x**. Place your bet to start!")



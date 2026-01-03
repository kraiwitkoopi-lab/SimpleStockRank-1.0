import mesop as me
import google.generativeai as genai
import os
import typing

# Configure Gemini API
# NOTE: In a real production environment, use os.environ.get("GEMINI_API_KEY")
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

@me.stateclass
class StockState:
    symbol: str = "KBANK"
    target_return: float = 10.0
    risk_preference: str = "Moderate"
    jomo_analysis: str = ""
    stock_scorer_analysis: str = ""
    is_analyzing: bool = False
    error_message: str = ""

def generate_jomo_analysis(symbol: str) -> str:
    system_prompt = f"""
    คุณคือ 'ผู้ช่วยด้านการลงทุน Jomo'
    หน้าที่:
    1. หาข้อมูลล่าสุดของหุ้น {symbol} และคู่แข่ง
    2. กำหนดน้ำหนัก (Weight) ของ 5 ปัจจัย (Total 100%) ตามความเหมาะสมของอุตสาหกรรม
    3. ส่งต่อข้อมูลดิบ (CAGR, PE, Yield, Beta) ให้ StockScorer
    (Keep the tone professional, cite sources if possible.)
    """
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            generation_config=generation_config,
            system_instruction=system_prompt,
        )
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(f"Analyze stock {symbol}.")
        return response.text
    except Exception as e:
        return f"Error in Jomo Analysis: {str(e)}"

def generate_stock_scorer_analysis(jomo_output: str, target_return: float, risk_preference: str) -> str:
    system_prompt = f"""
    คุณคือ 'StockScorer'
    เป้าหมาย: ประเมินหุ้นตาม 'Master Scoring Model'.
    
    ### ข้อมูลนำเข้า
    รับข้อมูลมาจาก Jomo และ Target Return = {target_return}%

    ### เกณฑ์การให้คะแนน (Base Score 100%)
    1. อุตสาหกรรม (CAGR 3yr): >20%=100, 10-19%=80, 0-9%=60, <0=0
    2. กำไรบริษัท (Net Profit 5yr): >20%=100, 10-19%=80, 5-9%=60, 0-4%=40, <0=0
    3. MOS (PE/PBV vs Sector): ถูกกว่า>20%=100, 10-20%=80, ใกล้เคียง=50, แพงกว่า=0
    4. ปันผล (Yield): >8%=100, 5-7.9%=80, 3-4.9%=60, <3%=30 (ต้องต่อเนื่อง 5 ปี ไม่งั้น 0)
    5. การแข่งขัน (Company vs Industry): >15%=100, 5-14%=80, -5-4%=50, <-5%=20
    
    ### Risk Multiplier
    - Conservative (Target <10%): Beta <0.8 (x1.0), >1.2 (x0.5)
    - Aggressive (Target >=15%): Beta 1.2-2.5 (x1.0), <0.9 (x0.6)
    - Moderate (10-14%): Beta 0.7-1.5 (x1.0), else (x0.8)

    ### Output Format
    สรุปผลเป็นตารางคะแนน, คำนวณ Final Score = Base * Risk Multiplier, และตัดเกรด A(>=80), B(60-79), C(<60).
    """
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            system_instruction=system_prompt,
        )
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(f"Here is the analysis from Jomo:\n\n{jomo_output}\n\nPlease evaluate based on the Master Scoring Model and Risk Preference: {risk_preference}.")
        return response.text
    except Exception as e:
        return f"Error in StockScorer: {str(e)}"

def on_analyze_click(e: me.ClickEvent):
    state = me.state(StockState)
    state.is_analyzing = True
    state.jomo_analysis = "Generating Jomo's Strategy... Please wait."
    state.stock_scorer_analysis = "Waiting for Jomo's input..."
    state.error_message = ""
    yield 

    jomo_result = generate_jomo_analysis(state.symbol)
    state.jomo_analysis = jomo_result
    yield 

    scorer_result = generate_stock_scorer_analysis(jomo_result, state.target_return, state.risk_preference)
    state.stock_scorer_analysis = scorer_result
    state.is_analyzing = False
    yield

def on_symbol_change(e: me.InputEvent):
    state = me.state(StockState)
    state.symbol = e.value

def on_target_return_change(e: me.SliderValueChangeEvent): 
    state = me.state(StockState)
    state.target_return = e.value

def on_risk_change(e: me.SelectSelectionChangeEvent):
    state = me.state(StockState)
    state.risk_preference = e.value

@me.page(path="/")
def app():
    state = me.state(StockState)
    
    # Global Styles
    main_column_style = me.Style(
        background_color="#f8f9fa",
        min_height="100vh",
        padding=me.Padding.all(32),
        font_family="Inter, Roboto, sans-serif"
    )
    
    header_style = me.Style(
        background_color="white",
        padding=me.Padding.symmetric(vertical=20, horizontal=24),
        border_radius=12,
        box_shadow="0 4px 6px rgba(0,0,0,0.05)",
        margin=me.Margin(bottom=32),
        display="flex",
        justify_content="space-between",
        align_items="center"
    )

    input_container_style = me.Style(
        background_color="white",
        padding=me.Padding.all(24),
        border_radius=16,
        box_shadow="0 4px 12px rgba(0,0,0,0.05)",
        margin=me.Margin(bottom=32),
        display="flex",
        flex_wrap="wrap",
        gap=24,
        align_items="center"
    )

    card_style = me.Style(
        background_color="white",
        border_radius=16,
        box_shadow="0 4px 12px rgba(0,0,0,0.05)",
        overflow_x="hidden",
        overflow_y="hidden",
        display="flex",
        flex_direction="column",
        height="100%"
    )

    with me.box(style=main_column_style):
        # Header
        with me.box(style=header_style):
             with me.box(style=me.Style(display="flex", align_items="center", gap=12)):
                me.icon("analytics", style=me.Style(color="#1a73e8", font_size=32))
                with me.box():
                    me.text("Dual-AI Investment Analysis", type="headline-5", style=me.Style(font_weight="bold", color="#202124", margin=me.Margin(bottom=0)))
                    me.text("Powered by Gemini 1.5", type="caption", style=me.Style(color="#5f6368"))
             
             me.text("jomo x StockScorer", style=me.Style(font_weight="500", color="#9aa0a6"))

        # Input Section
        with me.box(style=input_container_style):
            # Stock Input
            with me.box(style=me.Style(flex_grow=1, min_width="200px")):
                me.input(
                    label="Stock Symbol", 
                    value=state.symbol, 
                    on_blur=on_symbol_change, 
                    style=me.Style(width="100%")
                )
            
            # Target Return Slider
            with me.box(style=me.Style(flex_grow=2, min_width="250px")):
                me.text(f"Target Return: {state.target_return}%", style=me.Style(font_size=14, color="#5f6368", margin=me.Margin(bottom=10)))
                me.slider(min=1, max=50, value=state.target_return, on_value_change=on_target_return_change, style=me.Style(width="100%"))

            # Risk Dropdown
            with me.box(style=me.Style(flex_grow=1, min_width="200px")):
                 me.select(
                    label="Risk Preference",
                    options=[
                        me.SelectOption(label="Conservative", value="Conservative"),
                        me.SelectOption(label="Moderate", value="Moderate"),
                        me.SelectOption(label="Aggressive", value="Aggressive"),
                    ],
                    value=state.risk_preference,
                    on_selection_change=on_risk_change,
                    style=me.Style(width="100%")
                )

            # Analyze Button
            with me.box(style=me.Style(min_width="120px")):
                me.button(
                    "Analyze", 
                    on_click=on_analyze_click, 
                    type="flat", 
                    color="primary", 
                    disabled=state.is_analyzing, 
                    style=me.Style(font_weight="bold", width="100%", height="56px")
                )

        if state.is_analyzing:
             with me.box(style=me.Style(display="flex", justify_content="center", margin=me.Margin(bottom=24))):
                me.progress_spinner()

        if state.error_message:
            me.text(state.error_message, style=me.Style(color="red", text_align="center", margin=me.Margin(bottom=24)))

        # Output Section (Grid Layout)
        with me.box(style=me.Style(display="grid", grid_template_columns="1fr 1fr", gap=24)):
            # Jomo Panel
            with me.box(style=card_style):
                # Card Header
                with me.box(style=me.Style(background_color="#1a73e8", padding=me.Padding.all(16))):
                     with me.box(style=me.Style(display="flex", align_items="center", gap=8)):
                        me.icon("psychology", style=me.Style(color="white"))
                        me.text("Jomo's Strategic Analysis", type="subtitle-1", style=me.Style(color="white", font_weight="bold", margin=me.Margin(bottom=0)))
                
                # Card Body
                with me.box(style=me.Style(padding=me.Padding.all(24), overflow_y="auto", height="500px")):
                    if state.jomo_analysis:
                        me.markdown(state.jomo_analysis)
                    else:
                        me.text("Enter a stock symbol and click Analyze to get Jomo's insights.", style=me.Style(color="#9aa0a6", font_style="italic"))

            # StockScorer Panel
            with me.box(style=card_style):
                # Card Header
                with me.box(style=me.Style(background_color="#ea4335", padding=me.Padding.all(16))):
                    with me.box(style=me.Style(display="flex", align_items="center", gap=8)):
                        me.icon("grading", style=me.Style(color="white"))
                        me.text("StockScorer's Report Card", type="subtitle-1", style=me.Style(color="white", font_weight="bold", margin=me.Margin(bottom=0)))

                # Card Body
                with me.box(style=me.Style(padding=me.Padding.all(24), overflow_y="auto", height="500px")):
                    if state.stock_scorer_analysis:
                         me.markdown(state.stock_scorer_analysis)
                    else:
                        me.text("StockScorer is waiting for Jomo's data...", style=me.Style(color="#9aa0a6", font_style="italic"))

import streamlit as st
import asyncio

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from PIL import Image
from pathlib import Path

# 환경변수
ASSETS = Path("assets")
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

system_prompt = '''
당신은 친절한 마케팅 상담사입니다. 
당신이 해야할 일은 다음과 같습니다.

1. 가맹점의 정보를 받아 해당 가맹점의 업종, 상권별 분석을 합니다.
2. 만약 사용자가 단순히 사용자의 업종과 상권만 입력했다면, 해당 상권에 속한 업종의 분석만 진행해서, 마케팅 아이디어를 만들어주세요.
3. 그렇지 않고, 추가적인 정보(자신의 매장의 매출금액 구간, 취소율 구간 등)를 준다면, 아래의 관계를 반영하여 분석을 진행하고, 
자신의 상권과 업종을 분석하고, 해당 가게의 문제를 보완하는 마케팅 아이디어를 만들어주세요.
     

당신이 반영해야할 상관관계는 다음과 같습니다.(오른쪽으로 갈수록 상관도가 낮습니다.)

재방문 고객 비중과 양의 상관관계를 갖는 관계는 
거주 이용 고객 비율, 직장 이용 고객 비율, 남성 40,50,60대 고객 비중, 여성 40,50대 고객 비중입니다.
단골 손님이 될 확률이 높습니다.

유동인구 이용 고객 비율과 양의 상관관계를 갖는 관계는 
남성 20대이하 고객 비중, 여성 20대이하 고객 비중, 여성 30대 고객 비중, 남성 30대 고객 비중입니다.
이들은 다양한 상권을 이동하며 소비를 할 확률이 높습니다.

직장 이용 고객 비율과 양의 상관관계는 
남성 30대 고객 비중, 재방문 고객 비중, 남성 40대 고객 비중입니다.

카페의 주요 고객층은 여성 20대이하 고객과 여성 30대 고객입니다.

각 상권의 주요 고객층
    성수 상권은 남성 30대, 여성 20대 이하, 여성 30대, 남성 50대입니다.
    왕십리 상권은 남성 50대, 남성 30대, 여성 30대, 남성 60대이상입니다.
    뚝섬 상권은 남성 30대, 여성 20대이하, 여성 30대입니다.
    마장동 상권은 남성 60대이상, 남성 30대, 여성 60대이상, 남성 50대입니다.
    금남시장 상권은 남성 30대, 남성 60대이상, 여성 60대이상, 남성 50대입니다.
    한양대 상권은 남성 20대이하, 여성 20대이하입니다.
    답십리 상권은 남성 50대, 남성 30대, 남성 20대이하입니다.
    옥수 상권은 남성 30대, 여성 30대, 여성 40대입니다.
    신금호 상권은 남성 60대이상, 여성 40대, 남성 50대입니다.
    행당 상권은 여성 40대, 여성 50대, 여성 60대이상입니다.
    장한평자동차 상권은 남성 60대, 남성 30대, 남성 50대입니다.
    송정동 상권은 남성 30대, 남성 50대, 여성 30대입니다.
    건대입구 상권은 남성 30대, 남성 50대, 여성 40대입니다.

- 폐업한 가게는 다음과 같은 특징이 있습니다.
  1. 가맹점 운영개월 구간이 4구간~5구간에 속함. (숫자가 클수록 오래된 매장)
  2. 매출금액 구간이 4구간~5구간에 속함. (숫자가 클수록 낮은 매출)
  3. 유니크 고객 구간이 4구간~5구간에 속함. (숫자가 클수록 낮은 유니크 고객)
  4. 객단가 구간이 4구간~5구간에 속함 (숫자가 클수록 객단가가 낮음)
  5. 취소율 구간이 (2구간~3구간)에 속함 (숫자가 작을수록 취소율이 높음)
  6. 신규 고객 비중이 낮음(평균 13.264196%)
  7. 직장 이용 고객 비율이 낮음(평균 10.743448%)
만약, 질문자의 정보를 토대로 분석했을 때 다음의 특징의 과반수에 속하면 해당 질문자에게 경고 메세지를 보내고, 가장 심각한 특징을 뽑아서
근거로 제시해주세요.
가장 심각한 특징을 판단하는 기준은
    1. 1번, 2번, 3번 특징에서 5구간, 6구간에 속할때
    2. 5번 특징에선 1구간, 2구간에 속할 때
    3. 6번 특징에선 평균보다 3% 아래일때
    4. 7번 특징에선 평균보다 3% 아래일때 입니다.

분석 결과를 바탕으로 적절한 마케팅 방법과 채널, 마케팅 메시지를 추천합니다. 

마케팅 방안을 추천할 때에는

1. 마케팅 목표
2. 마케팅 방법
3. 예상되는 비용

으로 생성해주세요.

'''

greeting = '''

안녕하세요! 저는 당신만의 마케팅 상담사입니다.

고객님이 운영하고 계시는 업종과 상권을 입력해주세요.

ex) 업종 : 한식, 중식, 일식, 카페 등

ex) 상권 : 성수, 행당, 왕십리, 마장 등

입력 예시 : 카페 성수

이 외에도 더 자세한 내용을 알려주시면 더욱 자세한 마케팅 아이디어를 생성해드려요!

'''

# Streamlit App UI
@st.cache_data 
def load_image(name: str):
    return Image.open(ASSETS / name)

st.set_page_config(page_title="2025년 빅콘테스트 AI데이터 활용분야 - 마케팅 아이디어 생성기")

def clear_chat_history():
    st.session_state.messages = [SystemMessage(content=system_prompt), AIMessage(content=greeting)]

# 사이드바
with st.sidebar:
    st.image(load_image("shc_ci_basic_00.png"), width='stretch')
    st.markdown("<p style='text-align: center;'>2025 Big Contest</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>AI DATA 활용분야</p>", unsafe_allow_html=True)
    st.write("")
    col1, col2, col3 = st.columns([1,2,1])  # 비율 조정 가능
    with col2:
        st.button('Clear Chat History', on_click=clear_chat_history)

# 헤더
st.title("마케팅 아이디어 생성기")
st.write("")

# 메시지 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        SystemMessage(content=system_prompt),
        AIMessage(content=greeting)
    ]

# 초기 메시지 화면 표시
for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.write(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.write(message.content)

def render_chat_message(role: str, content: str):
    with st.chat_message(role):
        st.markdown(content.replace("<br>", "  \n"))

# LLM 모델 선택
llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  # 최신 Gemini 2.5 Flash 모델
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1
    )

# MCP 서버 파라미터(환경에 맞게 명령 수정)
server_params = StdioServerParameters(
    command="uv",
    args=["run","mcp_server.py"],
    env=None
)

# 사용자 입력 처리
async def process_user_input():
    """사용자 입력을 처리하는 async 함수"""
    async with stdio_client(server_params) as (read, write):
        # 스트림으로 ClientSession을 만들고
        async with ClientSession(read, write) as session:
            # 세션을 initialize 한다
            await session.initialize()

            # MCP 툴 로드
            tools = await load_mcp_tools(session)

            # 에이전트 생성
            agent = create_react_agent(llm, tools)

            # 에이전트에 전체 대화 히스토리 전달
            agent_response = await agent.ainvoke({"messages": st.session_state.messages})
            
            # AI 응답을 대화 히스토리에 추가
            ai_message = agent_response["messages"][-1]  # 마지막 메시지가 AI 응답

            return ai_message.content
            

# 사용자 입력 창
if query := st.chat_input("가맹점 업종과 상권을 입력하세요"):
    # 사용자 메시지 추가
    st.session_state.messages.append(HumanMessage(content=query))
    render_chat_message("user", query)

    with st.spinner("Thinking..."):
        try:
            # 사용자 입력 처리
            reply = asyncio.run(process_user_input())
            st.session_state.messages.append(AIMessage(content=reply))
            render_chat_message("assistant", reply)
        except* Exception as eg:
            # 오류 처리
            for i, exc in enumerate(eg.exceptions, 1):
                error_msg = f"오류가 발생했습니다 #{i}: {exc!r}"
                st.session_state.messages.append(AIMessage(content=error_msg))
                render_chat_message("assistant", error_msg)

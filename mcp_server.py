import pandas as pd
from pathlib import Path
from fastmcp.server import FastMCP, Context
from typing import List, Dict, Any, Optional

# 전역 데이터 저장
DF: Optional[pd.DataFrame] = None

# MCP 서버 초기화
mcp = FastMCP(
    "ZCD_BZN_SearchServer",
    instructions="""
    사용자의 업종과 상권을 바탕으로 마케팅 아이디어를 생성하는 서비스입니다.
    
    사용자가 업종과 상권을 입력하면 search_ZCD_BZN 함수를 사용하여 
    해당 상권에 속해 있고 그 상권에서 사용자와 같은 업종을 운영하고 있는 타 가맹점의 현 상태를
    분석해서 해당 상권의 주요 고객층과 고객 유형을 보여줍니다.
   
    업종과 상권은 부분일치를 허용합니다.
    
    검색 결과에는 다음 정보가 포함됩니다:
        - 해당 상권의 주요 고객층
        - 그 상권에 속하는 업종의 주요 고객층
        - 그 상권에 속하는 업종의 고객 유형 비중
    """
)

# 데이터 로드 함수
def _load_df():
    global DF
    DF = pd.read_csv("./data/df_join_open_stores_drop_grouped.csv")
    return DF

# 서버 시작 시 데이터 로드
_load_df()

@mcp.tool()
def search_ZCD_BZN(BZN : str, ZCD : str) -> Dict[str, Any]:
    """
    상권과 업종을 입력받아 해당 가맹점 정보를 검색합니다.
    
    매개변수:
      - BZN : 검색할 상권
      - ZCD : 검색할 업종
    
    반환값:
      -  해당 상권에 속해 있고 그 상권에서 사용자와 같은 업종을 운영하고 있는 타 가맹점의 현 상황
    """
    try:
    
        result = DF[(DF["상권"] == BZN) & (DF["업종"] == ZCD)]
    
        if len(result) == 0:
            return {
                "found": False,
                "message": f"'{BZN}' 상권에서 '{ZCD}' 업종에 해당하는 영업 중인 가맹점을 찾을 수 없습니다.",
                "count": 0,
                "stores": []
         }
    
    # 결과를 딕셔너리로 변환
        stores = result.to_dict(orient='records')

        return {
            "found": True,
            "message": f"'{BZN}' 상권의 '{ZCD}' 업종에 해당하는 영업 중인 가맹점 {len(stores)}개를 찾았습니다.",
            "count": len(stores),
            "stores": stores
        }
    except Exception as e:
        print(f"!!!!!! Tool 함수 내부에서 심각한 오류 발생: {e} !!!!!!")
        return {
            "found": False,
            "message": f"데이터 검색 중 내부 오류가 발생했습니다: {e}",
            "stores": []
        }

if __name__ == "__main__":
    mcp.run()
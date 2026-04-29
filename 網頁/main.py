from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# 允許跨網域存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載圖片資料夾 (對應您電腦裡的 image 資料夾) 
app.mount("/image", StaticFiles(directory="image"), name="image")

# 資料庫連線資訊 
conn_params = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "123456", # ⚠️ 請在此處填入您的密碼
    "host": "localhost",
    "port": "5432"
}

def get_db_conn():
    return psycopg2.connect(**conn_params, cursor_factory=RealDictCursor)

@app.get("/api/recipes")
def get_all_recipes():
    conn = get_db_conn()
    cur = conn.cursor()
    # SQL 指令包含分類 ID 以利前端篩選 [cite: 38, 40, 58]
    query = """
    SELECT r.id, r.name, r.image_url, r.servings, r.category_id,
           array_agg(i.name || ' ' || ri.amount || ri.unit) as ingredients
    FROM recipes r
    LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
    LEFT JOIN ingredients i ON ri.ingredient_id = i.id
    GROUP BY r.id, r.name, r.image_url, r.servings, r.category_id;
    """
    cur.execute(query)
    recipes = cur.fetchall()
    cur.close()
    conn.close()
    return recipes

@app.get("/api/recipes/{recipe_id}/steps")
def get_recipe_steps(recipe_id: int):
    conn = get_db_conn()
    cur = conn.cursor()
    # 根據步驟順序撈取詳細文字 [cite: 68, 69, 70, 75, 76]
    cur.execute("SELECT step_number, description FROM recipe_steps WHERE recipe_id = %s ORDER BY step_number", (recipe_id,))
    steps = cur.fetchall()
    cur.close()
    conn.close()
    if not steps:
        raise HTTPException(status_code=404, detail="找不到步驟")
    return steps

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
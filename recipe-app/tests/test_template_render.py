from jinja2 import Environment,FileSystemLoader,StrictUndefined,select_autoescape
from types import SimpleNamespace
from pathlib import Path
import datetime
E=Environment(loader=FileSystemLoader('views'),undefined=StrictUndefined,autoescape=select_autoescape())
labels=dict(hand='手部',leg='腳部',ball='球類',full_body='全身')
base=dict(caregiver=dict(center_name='示範照護中心',display_name='示範照護者'),page='dashboard',category_labels=labels,request=SimpleNamespace(url=SimpleNamespace(query='q=林&sort=desc')))
trend=[dict(date=f'2026-11-{n:02}',hand=n%5,leg=4,ball=3,full_body=1) for n in range(22,29)]
breakdown={k:dict(total=3,items=[dict(exercise_name='示範運動',count=3)]) for k in labels}
diet=[dict(week_monday='2026-11-23',vegetable_score=4,fried_score=2,variety_score=3,ai_observation='示範評語，非真實資料。')]
contexts=[('login',dict(error='',username='',next='/care')),('dashboard',dict(base,trend=trend,resident_count=12,avg_per_day=1.2,avg_per_week=8.4,avg_days_active_week=3.2,avg_days_active_month=15)),('residents',dict(base,page='residents',q='',sort='desc',selected_categories=[],residents=[dict(username='林○美',user_id=1,hand_count=4,leg_count=3,ball_count=2,full_body_count=1,total_count=10,last_completed_date='2026-11-27')])),('resident_detail',dict(base,page='residents',resident=dict(username='林○美',user_id=1),range='week',range_label='最近 7 天',back='q=林',trend=trend,breakdown=breakdown,diet=diet))]
for name,c in contexts:
 html=E.get_template('care/'+name+'.html').render(**c); print(name,'OK',len(html))
 if name!='login':
  if name=='dashboard':c['trend']=[]
  if name=='residents':c['residents']=[]
  if name=='resident_detail':c.update(trend=[],diet=[],breakdown={k:dict(total=0,items=[]) for k in labels})
  E.get_template('care/'+name+'.html').render(**c);print(name,'empty OK')

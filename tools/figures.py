"""Local editorial SVGs. No remote assets, logos, font files or account data."""
from pathlib import Path
from html import escape

C='#10B3CA'; O='#FF7A2A'; INK='#183B46'; LINE='#C6E4E9'; PALE='#ECF9FB'; DARK='#087086'; MUTED='#58717A'

def svg(width,height,title,desc,content):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc><style>text{{font-family:Inter,'Noto Sans CJK SC',sans-serif;fill:{INK};font-size:20px}}.small{{font-size:16px;fill:{MUTED}}}.num{{font-family:Inter,sans-serif}}</style>{content}</svg>'''

def text(x,y,s,**attrs):
    style=[]
    if 'font_size' in attrs:style.append(f"font-size:{attrs.pop('font_size')}px")
    if 'fill' in attrs:style.append(f"fill:{attrs.pop('fill')}")
    if style:attrs['style']=';'.join(style)
    if 'class_' in attrs:attrs['class']=attrs.pop('class_')
    attr=' '.join(f'{k.replace("_","-")}="{escape(str(v))}"' for k,v in attrs.items())
    return f'<text x="{x}" y="{y}" {attr}>{escape(s)}</text>'

def rect(x,y,w,h,stroke=C,fill='white',sw=2):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def line(x1,y1,x2,y2,stroke=C,sw=2,dash=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" '+(f'stroke-dasharray="{dash}"' if dash else '')+'/>'

def workspace():
    p=rect(12,89,192,70)+text(108,119,'准备好的文件',text_anchor='middle')+text(108,143,'与依赖基线',text_anchor='middle',class_='small')
    p+=f'<path d="M204 124 H269 V48 H317 M269 124 V204 H317" stroke="{C}" stroke-width="3" fill="none"/>'
    p+=rect(317,16,145,64)+text(389,56,'环境 A',text_anchor='middle')+rect(317,172,145,64)+text(389,212,'环境 B',text_anchor='middle')
    p+=line(462,48,523,48,O,3)+line(462,204,523,204,O,3)
    p+=rect(523,16,182,64,O)+text(614,55,'修改 · 检查',text_anchor='middle')+rect(523,172,182,64,O)+text(614,211,'修改 · 检查',text_anchor='middle')
    p+=line(719,16,719,236,LINE,2)+text(360,125,'同一个起点，独立试验',text_anchor='middle',class_='small')
    return svg(740,255,'同一个基线，两份文件环境','准备好的文件和依赖基线分别恢复为环境 A 与 B。两边独立修改和检查，不表示进程恢复或结果自动合并。',p)

def runtime_cost():
    p=text(0,24,'每次 2 分钟的任务',font_weight='600')+text(738,24,'同一规格 · 100 次／月',text_anchor='end',class_='small')
    x0=154; unit=45; y1=65; y2=143
    p+=text(0,96,'立即关闭')+text(0,174,'多等十分钟')
    p+=rect(x0,y1,unit*2,46,C,C,0)+rect(x0,y2,unit*2,46,C,C,0)+rect(x0+unit*2,y2,unit*10,46,O,O,0)
    p+=text(x0+45,y1+29,'2 min',text_anchor='middle',font_weight='600')+text(x0+45,y2+29,'2 min',text_anchor='middle',font_weight='600')
    p+=text(x0+unit*7,y2+29,'空闲 10 min',text_anchor='middle',font_weight='600')
    for tick in range(0,13,2):
        x=x0+unit*tick;p+=line(x,208,x,215,LINE,1.5)+text(x,241,str(tick),text_anchor='middle',class_='small')
    p+=line(x0,208,x0+unit*12,208,LINE,1.5)
    p+=text(739,241,'分钟',text_anchor='end',class_='small')
    p+=text(0,286,'内存用量：13.33 → 80 GiB·小时／月',font_weight='600')
    p+=text(0,315,'运行时长变成 6 倍；CPU 不把空闲时间按满载计算。',class_='small')
    return svg(740,335,'关闭时间改变内存用量','相同 4 GiB 配置每月执行100次。立即关闭每次2分钟，总内存13.33GiB小时；每次另空闲10分钟，总内存80GiB小时。条长按0至12分钟同一尺度绘制。',p)

def two_routes():
    p=text(0,23,'A  /  程序运行在平台上',font_weight='600')
    coords=[(0,44,145,'浏览器'),(238,44,176,'Worker'),(508,44,218,'绑定的数据资源')]
    for x,y,w,label in coords:p+=rect(x,y,w,62)+text(x+w/2,y+38,label,text_anchor='middle')
    p+=line(145,75,237,75,C,2)+line(414,75,508,75,C,2)
    p+=text(0,150,'B  /  程序留在原设备',font_weight='600')
    for x,y,w,label in [(0,172,145,'浏览器'),(238,172,176,'Tunnel'),(508,172,218,'原有应用与数据')]:
        p+=rect(x,y,w,62,O)+text(x+w/2,y+38,label,text_anchor='middle')
    p+=line(145,203,238,203,O,2)+line(414,203,508,203,O,2)
    p+=text(0,273,'需要私人访问时，在入口安排 Access 与应用授权。',class_='small')
    return svg(740,292,'两种应用入口','路线A：浏览器到Worker，再到绑定的数据资源。路线B：浏览器经Tunnel到原有应用与数据。私人访问另外安排Access与应用授权。',p)

def task_state():
    p=''
    for x,label in [(0,'已接收'),(266,'执行中'),(536,'结果已确认')]:
        p+=rect(x,20,190,64,C,PALE if x==536 else 'white')+text(x+95,59,label,text_anchor='middle',font_weight='600')
    p+=line(190,52,266,52,C,3)+line(456,52,536,52,C,3)
    p+=f'<path d="M361 84 V144 H455" fill="none" stroke="{O}" stroke-width="3"/>'
    p+=rect(455,113,271,64,O)+text(590,152,'结果未知 → 先核对',text_anchor='middle')
    p+=text(0,142,'不要把“已接收”当作“已完成”。',class_='small')
    p+=text(0,205,'只画主要关系；重试、取消与重复投递见状态表。',class_='small')
    return svg(740,225,'接收、执行与完成是不同阶段','任务由已接收到执行中，再到结果已确认。如果执行的外部结果未知，先进入核对，而不是盲目再做。这里只画主要关系，不是完整状态机。',p)

FIGS={'workspace':workspace,'runtime-cost':runtime_cost,'two-routes':two_routes,'task-state':task_state}

def write_all(root:Path):
    dest=root/'assets';dest.mkdir(exist_ok=True)
    for name,fun in FIGS.items():(dest/f'{name}.svg').write_text(fun(),encoding='utf-8')

if __name__=='__main__':write_all(Path(__file__).resolve().parents[1])

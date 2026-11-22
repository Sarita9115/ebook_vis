"""3.ranking_crecimiento — cartograma esquemático nacional + ranking CONAPO.

Datos: cve_ent, estado, poblacion_2020, poblacion_2025, crecimiento_pct,
       tasa_anual_pct, puesto; EIC 2025 como referencia de tres estados (opcional).
Fuente principal: CONAPO reconstrucciones/proyecciones municipales 1990–2040.
Posiciones de hexágonos: cartograma conceptual, NO límites geográficos ni área real.
"""
import math
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

BG = '#F7F7F2'
INK = '#1C3E39'
MUTED = '#64746D'
GREEN = '#256F5E'
BRICK = '#C67859'
GRID = '#DCE5DD'
PALETTE = [[0,'#D4E5DD'],[.24,'#91C6B1'],[.52,'#51A084'],[.78,'#2C806C'],[1,'#145244']]

# Cartograma hexagonal esquemático de las 32 entidades: orden geográfico aproximado.
# Es intencionalmente un tile map, no cartografía ni superficie estatal.
TILES = {
 '02':(1,1), '03':(2,3), '26':(3,1), '05':(5,2), '08':(4,3),
 '25':(4,5), '10':(5,5), '19':(7,3), '28':(8,3), '32':(6,6),
 '18':(5,7), '01':(7,6), '24':(8,5), '14':(6,8), '06':(6,9),
 '16':(7,9), '11':(8,8), '22':(9,8), '13':(10,7), '15':(9,10),
 '09':(10,10), '17':(10,11), '12':(8,11), '29':(11,9), '21':(11,10),
 '30':(12,7), '20':(11,12), '07':(13,12), '27':(13,9), '04':(14,10),
 '31':(15,9), '23':(16,10),
}
# Etiquetas de 2-3 letras, con nombre completo al pasar el cursor.
ABBR = {
 '01':'AGS','02':'BC','03':'BCS','04':'CAM','05':'COAH','06':'COL',
 '07':'CHIS','08':'CHIH','09':'CDMX','10':'DGO','11':'GTO','12':'GRO',
 '13':'HGO','14':'JAL','15':'MEX','16':'MICH','17':'MOR','18':'NAY',
 '19':'NL','20':'OAX','21':'PUE','22':'QRO','23':'QROO','24':'SLP',
 '25':'SIN','26':'SON','27':'TAB','28':'TAMPS','29':'TLAX','30':'VER',
 '31':'YUC','32':'ZAC'}

def _hex(cx,cy,r=.70):
    return [cx+r*math.cos(math.radians(60*i+30)) for i in range(7)], [cy+r*math.sin(math.radians(60*i+30)) for i in range(7)]

def _colorscale(value,lo,hi):
    t = (float(value)-lo)/(hi-lo) if hi>lo else .5
    return sample_colorscale(PALETTE, [max(0,min(1,t))])[0]

def figura(datos) -> go.Figure:
    fig=go.Figure()
    fig.update_layout(autosize=True,height=810,paper_bgcolor=BG,plot_bgcolor=BG,
      margin=dict(l=45,r=45,t=108,b=82),font=dict(family='Arial, sans-serif',color=INK,size=14),
      showlegend=False,hoverlabel=dict(bgcolor='white',font=dict(size=13,color=INK)),
      title=dict(text='<b>El pulso demográfico de México</b><br><sup>Variación de población por entidad federativa · 2020–2025</sup>',x=.035,y=.97, font=dict(size=24,color=INK)))
    if datos is None or len(datos)==0:return fig
    d=pd.DataFrame(datos).copy()
    required={'cve_ent','estado','poblacion_2020','poblacion_2025','crecimiento_pct','puesto'}
    missing=required.difference(d.columns)
    if missing:raise ValueError(f'Faltan campos: {sorted(missing)}')
    d['cve_ent']=d.cve_ent.astype(str).str.zfill(2)
    d=d.sort_values('crecimiento_pct',ascending=False).reset_index(drop=True)
    assert len(d)==32 and len(set(d.cve_ent))==32, 'Se requieren las 32 entidades sin duplicados'
    low=float(d.crecimiento_pct.min()); high=float(d.crecimiento_pct.max())
    for row in d.itertuples():
        code=row.cve_ent
        if code not in TILES:continue
        x0,y0=TILES[code]; cx=x0*.98; cy=-y0*.93
        xs,ys=_hex(cx,cy,.63)
        clr=_colorscale(row.crecimiento_pct,low,high)
        fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines',fill='toself',fillcolor=clr,
          line=dict(color=BG,width=3.3),showlegend=False,hoveron='fills',
          customdata=[[row.estado,row.poblacion_2020,row.poblacion_2025,row.crecimiento_pct,int(row.puesto)]]*len(xs),
          hovertemplate='<b>%{customdata[0]}</b> · puesto %{customdata[4]} / 32<br>2020: %{customdata[1]:,.0f}<br>2025: %{customdata[2]:,.0f}<br>Variación: <b>%{customdata[3]:+.2f}%</b><extra></extra>'))
        fig.add_trace(go.Scatter(x=[cx],y=[cy],mode='text',text=[f'<b>{ABBR[code]}</b>'],
             textfont=dict(size=10 if len(ABBR[code])<=3 else 8,color='white' if row.crecimiento_pct > low+(high-low)*.42 else INK),
             hoverinfo='skip',showlegend=False))
        if code=='31':
            xh,yh=_hex(cx,cy,.65)
            fig.add_trace(go.Scatter(x=xh,y=yh,mode='lines',line=dict(color=BRICK,width=3.5),hoverinfo='skip',showlegend=False))
    fig.update_xaxes(domain=[.01,.62],range=[.2,17.2],visible=False,fixedrange=True)
    fig.update_yaxes(domain=[.11,.88],range=[-12.7,.15],visible=False,scaleanchor='x',scaleratio=1,fixedrange=True)
    # Ranking legible 16 a la vez, con el botón de página. Los 32 permanecen en el cartograma.
    def ranked(page):
        a=d.iloc[16*page:16*(page+1)].copy()
        vals=a.crecimiento_pct.to_list(); names=a.estado.to_list()
        y=list(range(len(a)))[::-1]
        xx=[];yy=[]
        for n,v in zip(y,vals):xx.extend([0,float(v),None]); yy.extend([n,n,None])
        return [go.Scatter(x=xx,y=yy,mode='lines',line=dict(width=4,color='#C3D5CB'),xaxis='x2',yaxis='y2',showlegend=False,hoverinfo='skip'),
            go.Scatter(x=vals,y=y,mode='markers+text',marker=dict(size=[17 if n=='Yucatán' else 12 for n in names],color=[BRICK if n=='Yucatán' else GREEN for n in names],line=dict(color='white',width=1)),
               text=[f'{v:+.1f}%' for v in vals],textposition='middle right',textfont=dict(size=11,color=INK),
               customdata=list(zip(names,a.puesto,a.poblacion_2020,a.poblacion_2025)),
               hovertemplate='<b>#%{customdata[1]} · %{customdata[0]}</b><br>2020: %{customdata[2]:,.0f}<br>2025: %{customdata[3]:,.0f}<br>Crecimiento: %{x:+.2f}%<extra></extra>',xaxis='x2',yaxis='y2',showlegend=False)]
    fig.add_traces(ranked(0))
    fig.update_layout(xaxis2=dict(anchor='y2',domain=[.79,.97],range=[min(-.6,low-1),high+3.8],tickfont=dict(size=11),gridcolor=GRID,zeroline=True,zerolinecolor='#B6C5BB',ticksuffix='%'),
      yaxis2=dict(anchor='x2',domain=[.11,.86],range=[-.85,15.7],tickvals=list(range(15,-1,-1)),
                 ticktext=d.iloc[:16].estado.to_list(),tickfont=dict(size=11,color=INK),side='left',showgrid=False,automargin=True))
    extra = dict(xref='paper',yref='paper',showarrow=False,align='left')
    yuc=d[d.cve_ent=='31'].iloc[0]
    fig.add_annotation(x=.015,y=.96,text='<b>01 · MAPA DE MÉXICO</b>',font=dict(size=13,color=INK),**extra)
    fig.add_annotation(x=.015,y=.91,text='Crecimiento acumulado (%) · disposición hexagonal esquemática.',font=dict(size=11,color=MUTED),**extra)
    fig.add_annotation(x=.685,y=.96,text='<b>02 · RANKING NACIONAL</b>',font=dict(size=13,color=INK),**extra)
    fig.add_annotation(x=.685,y=.90,text='Crecimiento poblacional acumulado, 2020–2025',font=dict(size=11,color=MUTED),**extra)
    fig.add_annotation(x=.025,y=.06,text=f'<b>YUCATÁN</b>  ·  #{int(yuc.puesto)} de 32   ·   <b>{yuc.crecimiento_pct:+.2f}%</b> en cinco años',font=dict(size=17,color=BRICK),**extra)
    fig.add_annotation(x=.025,y=.015,text='Fuente: CONAPO · Reconstrucción 2020 y proyección 2025.',font=dict(size=11,color=MUTED),**extra)
    fig.update_layout(updatemenus=[dict(type='buttons',direction='right',showactive=True,x=.974,y=.94,xanchor='right',yanchor='top',bgcolor='white',bordercolor=GRID,
       buttons=[dict(label='1–16',method='update',args=[{'x':[None]*64},{'yaxis2.ticktext':d.iloc[:16].estado.to_list()}]),
                dict(label='17–32',method='update',args=[{'x':[None]*64},{'yaxis2.ticktext':d.iloc[16:32].estado.to_list()}])])])
    # 'update' with x=None intentionally avoided: instead use frame animation for the ranking traces only.
    fig.update_layout(updatemenus=[])
    fig.frames=[go.Frame(name=str(k),data=ranked(k),traces=[len(fig.data)-2,len(fig.data)-1],
                         layout=go.Layout(yaxis2=dict(ticktext=d.iloc[k*16:(k+1)*16].estado.to_list()))) for k in [0,1]]
    fig.update_layout(updatemenus=[dict(type='buttons',direction='right',x=.971,y=.955,xanchor='right',yanchor='top',showactive=True,
       bgcolor='white',bordercolor=GRID,buttons=[dict(label=f'{k*16+1}–{(k+1)*16}',method='animate',args=[[str(k)],dict(mode='immediate',frame=dict(duration=0,redraw=True),transition=dict(duration=0))]) for k in [0,1]])])
    return fig

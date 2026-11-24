"""3.poblacion_joven — mapa municipal interactivo (sin mapas base externos) y ranking.

Datos mixtos: fila_tipo='dato' (cvegeo, municipio, anio, jovenes, poblacion,
porcentaje, tipo) y fila_tipo='geometria' (cvegeo, geometry JSON EPSG:4326).
Jóvenes = 15–29 años. CONAPO 1990–2040, reconstrucción y proyección.
"""
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
from shapely.geometry import shape

BG='#F7F7F2';INK='#1A3D37';MUTE='#68796E';GREEN='#247962';BRICK='#BA7153';GRID='#DDE7DE'
COLORS=[[0,'#DFEDE0'],[.2,'#B7D8BF'],[.5,'#77B497'],[.75,'#3E856F'],[1,'#185446']]


def figura(datos)->go.Figure:
    fig=go.Figure()
    fig.update_layout(autosize=True,height=815,paper_bgcolor=BG,plot_bgcolor=BG,showlegend=False,
      margin=dict(l=43,r=38,t=108,b=110),font=dict(family='Arial, sans-serif',size=13,color=INK),
      title=dict(text='<b>Las nuevas generaciones de Yucatán</b><br><sup>Distribución de la población joven (15–29 años) · 1990–2040</sup>',x=.035,y=.972,font=dict(size=25,color=INK)),
      xaxis=dict(domain=[.035,.64],range=[-90.65,-87.30],visible=False,showgrid=False,zeroline=False,fixedrange=True),
      yaxis=dict(domain=[.15,.89],range=[19.30,21.87],visible=False,showgrid=False,zeroline=False,fixedrange=True,
                 scaleanchor='x',scaleratio=1/np.cos(np.deg2rad(20.7))),
      xaxis2=dict(anchor='y2',domain=[.82,.97],range=[0,34],ticksuffix='%',gridcolor=GRID,zeroline=False,tickfont=dict(size=11)),
      yaxis2=dict(anchor='x2',domain=[.19,.86],range=[-.8,9.8],tickvals=list(range(10)),tickfont=dict(size=11),showgrid=False,zeroline=False,automargin=True),
      hoverlabel=dict(bgcolor='white',font=dict(color=INK,size=12)))
    if datos is None or len(datos)==0:return fig
    df=pd.DataFrame(datos).copy()
    if 'fila_tipo' not in df:raise ValueError('Falta fila_tipo (dato o geometria)')
    raw_geo=df[df.fila_tipo=='geometria'];d=df[df.fila_tipo=='dato'].copy()
    d.cvegeo=d.cvegeo.astype(str).str.zfill(5)
    for col in ('anio','poblacion','jovenes','porcentaje'):d[col]=pd.to_numeric(d[col])
    d['anio']=d.anio.astype(int)
    if len(raw_geo)!=106 or len(set(raw_geo.cvegeo))!=106:raise ValueError('Se requieren 106 geometrías municipales distintas')
    years=[a for a in [1990,2000,2010,2020,2025,2030,2035,2040] if a in set(d.anio)]
    if len(years)!=8 or d.groupby('anio').size().loc[years].ne(106).any():raise ValueError('Datos municipales-año incompletos')
    geo={};coords={};rep={}
    for r in raw_geo.itertuples():
        k=str(r.cvegeo).zfill(5)
        g=shape(json.loads(r.geometry) if isinstance(r.geometry,str) else r.geometry)
        geo[k]=g;pt=g.representative_point();rep[k]=(pt.x,pt.y)
        xx=[];yy=[]
        for poly in (g.geoms if g.geom_type=='MultiPolygon' else [g]):
            x,y=poly.exterior.xy
            xx+=list(x)+[None];yy+=list(y)+[None]
        coords[k]=(xx,yy)
    keys=sorted(geo)
    def get(year):
        a=d[d.anio==year].set_index('cvegeo').loc[keys].reset_index();a['lon']=a.cvegeo.map(lambda k:rep[k][0]);a['lat']=a.cvegeo.map(lambda k:rep[k][1])
        top=a.nlargest(9,'jovenes');rank=a.nlargest(10,'porcentaje').sort_values('porcentaje')
        pct=a.jovenes.sum()/a.poblacion.sum()*100; typ='RECONSTRUCCIÓN' if year<=2020 else 'PROYECCIÓN'
        return a,top,rank,pct,typ
    start=2025
    def fill(p):return sample_colorscale(COLORS,[float(np.clip((float(p)-13)/20,0,1))])[0]
    def tooltip(r):return (f'<b>{r.municipio}</b><br>15–29 años: {r.jovenes:,.0f}<br>'
                           f'Población: {r.poblacion:,.0f}<br><b>{r.porcentaje:.1f}%</b> es población joven')
    a,top,rank,pct,typ=get(start)
    for r in a.itertuples():
        xx,yy=coords[r.cvegeo]
        fig.add_trace(go.Scatter(x=xx,y=yy,xaxis='x',yaxis='y',mode='lines',fill='toself',fillcolor=fill(r.porcentaje),
           hoveron='fills',line=dict(color='#F9F8F3',width=1.0),showlegend=False,name=str(r.municipio),
           hoverinfo='text',text=tooltip(r),hovertemplate='%{text}<extra></extra>'))
    def bubble(t):
        return go.Scatter(x=t.lon,y=t.lat,xaxis='x',yaxis='y',mode='markers',
            marker=dict(size=10+32*np.sqrt(t.jovenes/t.jovenes.max()),color='rgba(187,110,73,.55)',line=dict(color='#9E593F',width=1.2)),
            customdata=t[['municipio','jovenes','porcentaje']].to_numpy(),
            hovertemplate='<b>%{customdata[0]}</b><br>Jóvenes: %{customdata[1]:,.0f}<br>Participación: %{customdata[2]:.1f}%<extra></extra>',showlegend=False)
    fig.add_trace(bubble(top))
    def ranks(r):
        y=list(range(10));vals=r.porcentaje.to_list()
        l=go.Scatter(x=[z for v in vals for z in [0,v,None]],y=[i for i in y for _ in [0,1,2]],
            xaxis='x2',yaxis='y2',mode='lines',line=dict(color='#BDCEC3',width=4),hoverinfo='skip',showlegend=False)
        p=go.Scatter(x=vals,y=y,xaxis='x2',yaxis='y2',mode='markers+text',
            marker=dict(color=GREEN,size=13,line=dict(color='white',width=1.6)),
            text=[f'{z:.1f}%' for z in vals],textposition='middle left',textfont=dict(color=INK,size=11),
            hovertemplate='%{x:.2f}% de jóvenes<extra></extra>',showlegend=False)
        return [l,p]
    fig.add_traces(ranks(rank))
    def annotations(y,pct,typ):
        return [dict(x=.023,y=.965,xref='paper',yref='paper',text='<b>01  ·  CONCENTRACIÓN TERRITORIAL</b>',showarrow=False,xanchor='left',font=dict(size=13,color=INK)),
          dict(x=.023,y=.921,xref='paper',yref='paper',text='Tono más oscuro = mayor porcentaje  ·  burbuja más grande = más jóvenes',showarrow=False,xanchor='left',font=dict(size=11,color=MUTE)),
          dict(x=.721,y=.965,xref='paper',yref='paper',text='<b>02  ·  MUNICIPIOS MÁS JÓVENES</b>',showarrow=False,xanchor='left',font=dict(size=13,color=INK)),
          dict(x=.721,y=.923,xref='paper',yref='paper',text='Los 10 municipios con mayor proporción',showarrow=False,xanchor='left',font=dict(size=11,color=MUTE)),
          dict(x=.025,y=.066,xref='paper',yref='paper',text=f'<b>{y}</b> · {typ}  |  {int(d[d.anio==y].jovenes.sum()):,} jóvenes · <b>{pct:.1f}%</b> de la población estatal',showarrow=False,xanchor='left',font=dict(size=14,color=INK)),
          dict(x=.025,y=.012,xref='paper',yref='paper',text='CONAPO · Reconstrucciones y proyecciones, 1990–2040 · Límites municipales INEGI.',showarrow=False,xanchor='left',font=dict(size=11,color=MUTE))]
    fig.update_layout(annotations=annotations(start,pct,typ),yaxis2=dict(ticktext=rank.municipio.to_list()))
    # Leyenda discreta de proporciones, en un lugar estable del pie del mapa.
    for i,(label,prop) in enumerate([('15%',15),('20%',20),('25%',25),('30%',30)]):
        xx=.21+i*.081
        fig.add_shape(type='rect',xref='paper',yref='paper',x0=xx,y0=.117,x1=xx+.028,y1=.134,
             fillcolor=fill(prop),line=dict(color='white',width=.8))
        fig.add_annotation(x=xx+.034,y=.126,xref='paper',yref='paper',text=label,showarrow=False,
             font=dict(size=10,color=MUTE),xanchor='left')
    fig.frames=[]
    for y in years:
        yr,t,r,pct,typ=get(y)
        frame=[go.Scatter(fillcolor=fill(row.porcentaje),name=str(row.municipio),text=tooltip(row),hovertemplate='%{text}<extra></extra>') for row in yr.itertuples()]
        frame.append(bubble(t));frame.extend(ranks(r))
        fig.frames+=(go.Frame(name=str(y),data=frame,traces=list(range(len(fig.data))),
                   layout=go.Layout(annotations=annotations(y,pct,typ),yaxis2=dict(ticktext=r.municipio.to_list()))),)
    fig.update_layout(sliders=[dict(active=years.index(start),x=.025,y=-.062,len=.90,currentvalue=dict(prefix='Año: '),
       steps=[dict(label=str(y),method='animate',args=[[str(y)],dict(mode='immediate',frame=dict(duration=280,redraw=True),transition=dict(duration=120))]) for y in years])],
       updatemenus=[dict(type='buttons',direction='right',x=.973,y=1.088,xanchor='right',yanchor='bottom',showactive=False,
          buttons=[dict(label='▶ Reproducir',method='animate',args=[None,dict(fromcurrent=True,frame=dict(duration=1100,redraw=True),transition=dict(duration=250))]),
                   dict(label='Ⅱ Pausar',method='animate',args=[[None],dict(mode='immediate',frame=dict(duration=0,redraw=False),transition=dict(duration=0))])])])
    return fig

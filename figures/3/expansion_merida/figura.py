"""3.expansion_merida — huella metropolitana con mapa histórico real y desgloses.

Tabla de oro mixta (fila_tipo):
  periodo    anio, hectareas, cambio_desde_2000, poblacion_censal_municipios, mapa_original_uri
  municipio  municipio, crecimiento_ha, area_urbana_2020
Fuente: Aguilar, Flores-Espinosa & Hernández (EURE, 2025), figura 1 y tabla 1, pp. 8–9.
AVISO: el mapa es imagen académica de los cuatro periodos; el selector no modifica esa imagen.
No se simulan polígonos georreferenciados históricos.
"""
import pandas as pd
import plotly.graph_objects as go

BG='#F7F7F2'; INK='#1A3F38'; MUTE='#63736A'; TEAL='#2D7767'; BRICK='#C47757'; GOLD='#E4B45F'; GRID='#DFE7DE'
PERIOD_COLOR={1993:'#D6B953',2000:'#E9A447',2010:'#C66D4D',2020:'#9D322E'}


def figura(datos)->go.Figure:
    fig=go.Figure()
    fig.update_layout(autosize=True,height=815,paper_bgcolor=BG,plot_bgcolor=BG,
       font=dict(family='Arial, sans-serif',color=INK,size=13),showlegend=False,
       title=dict(text='<b>Las huellas de una ciudad</b><br><sup>Zona Metropolitana de Mérida · Superficie urbanizada, 1993–2020</sup>',x=.034,y=.972,font=dict(size=24,color=INK)),
       margin=dict(l=42,r=42,t=112,b=108),hoverlabel=dict(bgcolor='white',font=dict(color=INK,size=12)),
       xaxis=dict(anchor='y',domain=[.015,.55],visible=False,range=[0,1],fixedrange=True),
       yaxis=dict(domain=[.20,.86],visible=False,range=[0,1],fixedrange=True),
       xaxis2=dict(anchor='y2',domain=[.67,.973],range=[1990,2023],tickvals=[1993,2000,2010,2020],showgrid=False,tickfont=dict(size=12)),
       yaxis2=dict(anchor='x2',domain=[.55,.86],range=[0,47500],gridcolor=GRID,zeroline=False,tickformat=',.0f',title=dict(text='Hectáreas',font=dict(size=11))),
       xaxis3=dict(anchor='y3',domain=[.735,.973],range=[0,13400],gridcolor=GRID,zeroline=False,tickformat='~s'),
       yaxis3=dict(anchor='x3',domain=[.18,.42],range=[-.7,6.8],tickvals=list(range(7)),showgrid=False,zeroline=False,tickfont=dict(size=11)))
    if datos is None or len(datos)==0:return fig
    d=pd.DataFrame(datos)
    if 'fila_tipo' not in d:raise ValueError('Falta fila_tipo en tabla de oro')
    area=d[d.fila_tipo=='periodo'].copy().sort_values('anio')
    muni=d[d.fila_tipo=='municipio'].copy().sort_values('crecimiento_ha',ascending=False)
    if len(area)!=4 or len(muni)<10:raise ValueError('Se necesitan 4 periodos y el desglose municipal de la tabla EURE')
    years=area.anio.astype(int).to_list(); sizes=area.hectareas.to_list()
    img=area.mapa_original_uri.dropna()
    if len(img):
        fig.add_layout_image(dict(source=img.iloc[0],xref='x domain',yref='y domain',x=0,y=1,
            sizex=1,sizey=1,sizing='contain',opacity=1,layer='below',xanchor='left',yanchor='top'))
    else:
        fig.add_annotation(x=.26,y=.58,xref='paper',yref='paper',text='Mapa académico no disponible',showarrow=False,font=dict(size=18,color=MUTE))
    fig.add_trace(go.Scatter(x=years,y=sizes,xaxis='x2',yaxis='y2',mode='lines+markers',
       line=dict(color=TEAL,width=5,shape='linear'),marker=dict(size=13,color=[PERIOD_COLOR[i] for i in years],line=dict(color='white',width=2)),
       fill='tozeroy',fillcolor='rgba(107,161,137,.14)',
       text=[f'{v:,.0f} ha' for v in sizes],textposition='top center',
       hovertemplate='<b>%{x}</b><br>Superficie construida: %{y:,.2f} ha<extra></extra>',showlegend=False))
    def marker(y):
        val=float(area.loc[area.anio==y,'hectareas'].iloc[0]);return go.Scatter(x=[y],y=[val],xaxis='x2',yaxis='y2',mode='markers',
            marker=dict(size=23,color=PERIOD_COLOR[y],line=dict(color=BG,width=5)),hoverinfo='skip',showlegend=False)
    fig.add_trace(marker(2020))
    top=muni.head(7).sort_values('crecimiento_ha')
    fig.add_trace(go.Bar(x=top.crecimiento_ha,y=list(range(7)),xaxis='x3',yaxis='y3',orientation='h',
        marker_color=[BRICK if name=='Mérida' else TEAL for name in top.municipio],
        text=[f'{x:,.0f}' for x in top.crecimiento_ha],textposition='outside',textfont=dict(size=11),cliponaxis=False,
        customdata=top[['municipio','area_urbana_2020']].to_numpy(),
        hovertemplate='<b>%{customdata[0]}</b><br>Nueva superficie 2000–2020: %{x:,.1f} ha<br>Área construida total 2020: %{customdata[1]:,.1f} ha<extra></extra>',showlegend=False))
    base2000=float(area.loc[area.anio==2000,'hectareas'].iloc[0])
    fixed=[
      dict(x=.017,y=.958,xref='paper',yref='paper',text='<b>01  ·  EL TERRITORIO</b>',font=dict(size=13,color=INK),showarrow=False,xanchor='left'),
      dict(x=.02,y=.918,xref='paper',yref='paper',text='Expansión territorial · 1993–2020',font=dict(size=11,color=MUTE),showarrow=False,xanchor='left'),
      dict(x=.60,y=.958,xref='paper',yref='paper',text='<b>02  ·  EL TIEMPO</b>',font=dict(size=13,color=INK),showarrow=False,xanchor='left'),
      dict(x=.60,y=.91,xref='paper',yref='paper',text='Superficie urbanizada · mismas 14 demarcaciones',font=dict(size=11,color=MUTE),showarrow=False,xanchor='left'),
      dict(x=.60,y=.495,xref='paper',yref='paper',text='<b>03  ·  ¿DÓNDE OCURRIÓ LA EXPANSIÓN?</b>',font=dict(size=13,color=INK),showarrow=False,xanchor='left'),
      dict(x=.60,y=.452,xref='paper',yref='paper',text='Mayores aumentos de superficie 2000–2020 (ha)',font=dict(size=11,color=MUTE),showarrow=False,xanchor='left'),
      dict(x=.60,y=.12,xref='paper',yref='paper',text='<b>TIPO DE EXPANSIÓN</b> · 60.1% contigua · 6.7% axial · 33.2% dispersa',font=dict(size=13,color=INK),showarrow=False,xanchor='left'),
      dict(x=.60,y=.064,xref='paper',yref='paper',text='Mapa histórico de los cuatro periodos · Fuente: Aguilar et al., EURE (2025).',font=dict(size=11,color=MUTE),showarrow=False,xanchor='left'),
    ]
    def title_for(y):
        val=float(area.loc[area.anio==y,'hectareas'].iloc[0]);delta=(val/base2000-1)*100
        return f'<b>Las huellas de una ciudad</b><br><sup>Zona Metropolitana de Mérida · {y} · {val:,.0f} hectáreas · {delta:+.1f}% respecto a 2000</sup>'
    fig.update_layout(title=dict(text=title_for(2020)),annotations=fixed,yaxis3=dict(ticktext=top.municipio.tolist()),
       sliders=[dict(x=.625,y=-.060,len=.33,active=len(years)-1,currentvalue=dict(prefix='Año seleccionado: ',font=dict(size=13)),
          steps=[dict(label=str(y),method='animate',args=[[str(y)],dict(mode='immediate',frame=dict(duration=200,redraw=True),transition=dict(duration=140))]) for y in years])])
    fig.frames=[go.Frame(name=str(y),data=[marker(y)],traces=[1],layout=go.Layout(title=dict(text=title_for(y)),annotations=fixed)) for y in years]
    return fig

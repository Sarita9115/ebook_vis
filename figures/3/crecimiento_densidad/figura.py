"""3.crecimiento_densidad — maqueta de parcelas y edificios proporcionales.

Columnas: cvegeo, municipio, anio, poblacion, densidad, superficie_km2,
          densidad_yucatan, crecimiento_2010_2020.
Fuente primaria INEGI, Censos 2010 y 2020, panorama sociodemográfico municipal.
"""
import pandas as pd
import plotly.graph_objects as go

BG = '#F7F7F2'; INK='#1B3D37'; MUTE='#62736A'; GREEN='#326E5D'; BRICK='#B76C4E'


def figura(datos) -> go.Figure:
    fig=go.Figure()
    fig.update_layout(autosize=True,height=790,margin=dict(l=56,r=36,t=112,b=82),
       title=dict(text='<b>Yucatán en miniatura</b><br><sup>Densidad poblacional por municipio · Censos 2010 y 2020</sup>',x=.04,y=.97,font=dict(size=25,color=INK)),
       paper_bgcolor=BG,plot_bgcolor=BG,font=dict(family='Arial, sans-serif',color=INK,size=13),showlegend=False,
       hoverlabel=dict(bgcolor='white',font=dict(size=13,color=INK)),
       xaxis=dict(domain=[.05,.665],range=[-.6,5.68],fixedrange=True,showgrid=False,zeroline=False,tickfont=dict(size=13)),
       yaxis=dict(domain=[.18,.87],fixedrange=True,zeroline=False,gridcolor='#DCE4DA',title=dict(text='Habitantes por km²',font=dict(size=12))),
       xaxis2=dict(anchor='y2',domain=[.795,.97],range=[0,1550],tickfont=dict(size=11),gridcolor='#DCE4DA',ticksuffix=''),
       yaxis2=dict(anchor='x2',domain=[.25,.81],range=[-.7,5.7],tickmode='array',tickvals=list(range(6)),ticktext=[],showticklabels=False,tickfont=dict(size=11),showgrid=False,zeroline=False))
    if datos is None or len(datos)==0:return fig
    d=pd.DataFrame(datos).copy(); d['anio']=pd.to_numeric(d['anio'],errors='raise');d['densidad']=pd.to_numeric(d.densidad)
    assert len(d[d.anio==2010])==len(d[d.anio==2020])==106
    vals=d.pivot(index='municipio',columns='anio',values='densidad')
    pop=d.pivot(index='municipio',columns='anio',values='poblacion')
    maxdens=float(d.densidad.max());depth=52
    ranks=d[d.anio==2020].sort_values('densidad',ascending=False)['municipio'].tolist()
    # Ranking anclado al censo 2020: se comparan los mismos municipios al cambiar de año.
    groups=[(f'Puestos {i+1}–{min(106,i+6)}',ranks[i:i+6]) for i in range(0,106,6)]
    def building(x,h,highlight=False):
        front=BRICK if highlight else GREEN
        side='#874D38' if highlight else '#1F4C40'; roof='#E1A58A' if highlight else '#8EB09E'
        def polygon(px,py,color):return go.Scatter(x=px,y=py,fill='toself',mode='lines',fillcolor=color,line=dict(color=color,width=.8),hoverinfo='skip',showlegend=False)
        parcel=polygon([x-.43,x+.31,x+.62,x-.12,x-.43],[-20,-20,-81,-81,-20],'#D6E5D4')
        wall=polygon([x-.24,x+.25,x+.25,x-.24,x-.24],[0,0,h,h,0],front)
        lateral=polygon([x+.25,x+.43,x+.43,x+.25,x+.25],[0,depth,h+depth,h,0],side)
        rooftop=polygon([x-.24,x+.25,x+.43,x-.06,x-.24],[h,h,h+depth,h+depth,h],roof)
        w_x=[];w_y=[]
        if h>100:
            for yy in range(76,int(h)-24,103):
                for xx in [x-.12,x+.10]:w_x.append(xx);w_y.append(yy)
        windows=go.Scatter(x=w_x,y=w_y,mode='markers',marker=dict(size=6,symbol='square',color='#F2E9CE',opacity=.86,line=dict(width=0)),hoverinfo='skip',showlegend=False)
        return [parcel,wall,lateral,rooftop,windows]
    def view(year,label,names):
        a=d[d.anio==year].set_index('municipio').loc[names].reset_index()
        top=float(a.densidad.max()); traces=[]
        for i in range(6):
            if i < len(a):
                r=a.iloc[i]; traces += building(i,float(r.densidad),float(r.densidad)==top)
            else:
                # En el último grupo hay cuatro municipios; no duplicar posiciones 1–2.
                traces += [go.Scatter(x=[],y=[],hoverinfo='skip',showlegend=False) for _ in range(5)]
        for i in range(6):
            if i>=len(a):
                traces.append(go.Scatter(x=[],y=[],hoverinfo='skip',showlegend=False))
                continue
            r=a.iloc[i]
            change=float(r.crecimiento_2010_2020)
            area='No publicada en panorama 2010' if pd.isna(r.superficie_km2) else f'{r.superficie_km2:,.1f} km²'
            txt=(f'<b>{r.municipio}</b><br>{year} · {r.poblacion:,} habitantes<br>'
                 f'{r.densidad:,.1f} hab/km²<br>Superficie: {area}<br>'
                 f'Crecimiento de población 2010–2020: {change:+.1f}%')
            traces.append(go.Scatter(x=[i],y=[r.densidad],mode='markers+text',
                marker=dict(size=27,opacity=0),text=[f'<b>{r.densidad:,.1f}</b>'],textposition='top center',
                textfont=dict(size=14,color=INK),hovertext=[txt],hovertemplate='%{hovertext}<extra></extra>'))
        # Dos puntos por municipio y la línea conectiva: comparativo persistente independiente del año.
        for j in range(6):
            if j>=len(names):
                traces.append(go.Scatter(x=[],y=[],xaxis='x2',yaxis='y2',hoverinfo='skip',showlegend=False))
                continue
            name=names[j]
            a10=float(vals.loc[name,2010]); a20=float(vals.loc[name,2020])
            traces.append(go.Scatter(x=[a10,a20],y=[5-j,5-j],xaxis='x2',yaxis='y2',mode='lines+markers',
                line=dict(width=3,color='#95AA9E'),marker=dict(size=[10,14],color=['#BFD6C6',BRICK if name=='Kanasín' else GREEN],line=dict(color='white',width=1)),
                hovertemplate=f'<b>{name}</b><br>2010: {a10:,.1f} hab/km²<br>2020: {a20:,.1f} hab/km²<extra></extra>',showlegend=False))
        cards=[]
        for j,name in enumerate(names):
            cards.append(dict(x=.776,y=.25+(5-j)*.56/5,xref='paper',yref='paper',text=name,showarrow=False,xanchor='right',
                  font=dict(size=11,color=INK)))
        cards.append(dict(x=.705,y=.885,xref='paper',yref='paper',showarrow=False,xanchor='left',text='<b>CAMBIO DE DENSIDAD · 2010–2020</b>',font=dict(size=14,color=INK)))
        cards.append(dict(x=.705,y=.842,xref='paper',yref='paper',showarrow=False,xanchor='left',text='Punto claro: 2010 · punto oscuro: 2020',font=dict(size=11,color=MUTE)))
        cards.append(dict(x=.035,y=.075,xref='paper',yref='paper',showarrow=False,xanchor='left',text=f'<b>YUCATÁN {year}</b> · {float(a.densidad_yucatan.iloc[0]):.1f} hab/km²   |   <b>106 municipios</b> en la fuente',font=dict(size=14,color=INK)))
        cards.append(dict(x=.035,y=.01,xref='paper',yref='paper',showarrow=False,xanchor='left',text='Altura = densidad (hab/km²) · INEGI, censos 2010 y 2020.',font=dict(size=11,color=MUTE)))
        return traces,cards,names+['']*(6-len(names))
    views=[]
    for label,names in groups:
        for year in [2020,2010]:views.append((year,label,names))
    v0=views[0]; traces,anns,names=view(*v0)
    fig.add_traces(traces)
    # Building traces tienen 5 por edificio + etiqueta 1 por edificio + 1 comparativo por edificio = 42.
    ntr=len(traces)
    assert ntr==42
    fig.update_layout(annotations=anns,
       yaxis=dict(range=[-105,maxdens*1.14]),
       xaxis=dict(tickvals=list(range(6)),ticktext=names,showticklabels=True))
    fig.frames=[];menu=[]
    for j,(year,label,ns) in enumerate(views):
        frame_data,frame_anns,frame_names=view(year,label,ns)
        fig.frames+=(go.Frame(name=str(j),data=frame_data,traces=list(range(ntr)),
                        layout=go.Layout(annotations=frame_anns,xaxis=dict(ticktext=frame_names))),)
        menu.append(dict(label=f'{year} · {label}',method='animate',args=[[str(j)],
                         dict(mode='immediate',frame=dict(duration=220,redraw=True),transition=dict(duration=160))]))
    fig.update_layout(updatemenus=[dict(type='dropdown',x=.985,xanchor='right',y=1.075,yanchor='bottom',showactive=True,
              bgcolor='white',bordercolor='#D0D9D0',font=dict(size=12),buttons=menu)])
    return fig

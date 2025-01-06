import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
import model
from bs4 import BeautifulSoup
from scipy.spatial import ConvexHull
import plotly.io as pio
import base64

db = sqlite3.connect('instance/playlists.db')
artist = pd.read_sql_query("SELECT * FROM artist", db).set_index('id')
playlist = pd.read_sql_query("SELECT * FROM playlist", db).set_index('id')
track = pd.read_sql_query("SELECT * FROM track", db).set_index('id')

colorway = ['#173a89', '#ca6d0b', '#7484F9', '#047640', '#BDBEC4', '#9E310C']

def percent_width(percent, width):
    return percent * width

def flatten(itr):
        for x in itr:
            try:
                yield from flatten(x)
            except:
                yield x

def spider_graph(playlist, recs, viewport):
    features = model.get_audio_features()
    # features.drop(['key', 'liveness'], axis=1, inplace=True)

    columns = features.columns
    for column in columns:
        features[column] = features[column] / features[column].abs().max()

    fig = go.Figure()

    playlists = [playlist]
    playlists.append(recs)
    playlists = flatten(playlists)
    for playlist in playlists:
        playlist_features = features.loc[features.index == playlist.playlist_id].values.flatten()
        fig.add_trace(go.Scatterpolar(
            r = playlist_features,
            theta = columns,
            fill = 'toself',
            name = playlist.name,
            mode = 'markers'
        ))
    fig.update_layout(
        title=dict(
            text="<b>audio features</b>",
            font=dict(
                size=25,
                color="black"), 
            automargin=True,
            yref='paper'),
        showlegend = True,
        paper_bgcolor='rgba(248,248,248,255)',
        plot_bgcolor='rgba(248,248,248,255)',
        font_family="Sans-Serif",
        colorway=colorway
    )

    if viewport < 768:
        graph_bytes = pio.to_image(fig, format='jpg')
        graph_image = base64.b64encode(graph_bytes).decode('utf-8')
        return graph_image
    else:
        graph_html = fig.to_html(full_html=False, config={'responsive': True, 'displayModeBar': True})
        return graph_html

def genres_scatter():
    with open('resources/enao.html', 'r', encoding='utf-8') as file:
        html_content = file.read()
    soup = BeautifulSoup(html_content, 'html.parser')

    genres = soup.find(class_='canvas')
    genre_map = {}
    for genre in genres.find_all(recursive=True):
        name = genre.text[:-2]
        style = genre.get('style', '')
        styles = dict(item.split(':') for item in style.split(';') if item.strip())
        top = styles.get(' top', '').strip()
        left = styles.get(' left', '').strip()
        color = styles.get('color', '').strip()
        genre_map[name] = [top, left, color]
    genre_map = {k: v for k, v in genre_map.items() if not k == ''}

    genre_data = [{'genre': genre, 'x': int(values[0][:-2]), 'y': int(values[1][:-2]), 'color': values[2]}for genre, values in genre_map.items()]
    genre_df = pd.DataFrame(genre_data)

    def get_coords(genre):
        try:
            return genre_df[genre_df['genre'] == genre]['x'].values[0], genre_df[genre_df['genre'] == genre]['y'].values[0]
        except:
            return (sum(genre_df['x']) / len(genre_df), sum(genre_df['y']) / len(genre_df))

    fig = go.Figure()
    for item in genre_data:
        fig.add_trace(
            go.Scatter(
                x=[item['x']],
                y=[item['y']],
                marker=dict(color=item['color'], size=5),
                name=item['genre'],
                opacity=0.5,
                hovertemplate=item['genre'],
                showlegend=False
            )
        )
    fig.update_layout(
        title=dict(
            text='<b>genre</b>',
            font=dict(
                size=25,
                color='black'), 
            automargin=True,
            yref='paper'),
        xaxis=dict(range=[0, max(genre_df['x'])]),
        yaxis=dict(range=[0, max(genre_df['y'])]),
        xaxis_title='← denser & atmospheric, spikier & bouncier →',
        yaxis_title='← organic, mechanical & electric →',
        paper_bgcolor='rgba(248,248,248,255)',
        plot_bgcolor='rgba(248,248,248,255)',
        font_family="Sans-Serif",
        height=800,
        # autosize=True
        # width=2000
    )
    fig.update_yaxes(
        scaleanchor='x',
        scaleratio=10
    )
    return fig, get_coords

def genres_graph(playlist, recs, viewport):
    all_playlist_genres = model.get_genres()
    fig, get_coords = genres_scatter()

    playlists = [playlist]
    playlists.append(recs)
    playlists = flatten(playlists)
    position = 0
    for this_playlist in playlists:
        playlist_genres = list(set(all_playlist_genres[all_playlist_genres['playlist_id'] == this_playlist.playlist_id]['genres'].values[0]))
        points = []
        for genre in playlist_genres:
            points.append(get_coords(genre))
        hull = ConvexHull(points)
        shape = np.array(points)[hull.vertices]
        shape = list(zip(*shape))
        
        fig.add_trace(
            go.Scatter(
                x=shape[0],
                y=shape[1],
                fill='toself',
                showlegend=True,
                name=this_playlist.name,
                line=dict(color=colorway[position]),
                hovertemplate=playlist_genres,
                mode='markers'
            )
        )
        position += 1

    if viewport < 768:
        graph_bytes = pio.to_image(fig, format='jpg')
        graph_image = base64.b64encode(graph_bytes).decode('utf-8')
        return graph_image
    else:
        graph_html = fig.to_html(full_html=False)
        return graph_html



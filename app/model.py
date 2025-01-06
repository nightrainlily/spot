import pandas as pd
import numpy as np
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD

db = sqlite3.connect('instance/playlists.db')
artist = pd.read_sql_query("SELECT * FROM artist", db).set_index('id')
playlist = pd.read_sql_query("SELECT * FROM playlist", db).set_index('id')
track = pd.read_sql_query("SELECT * FROM track", db).set_index('id')
tracklist = pd.read_sql_query("SELECT * FROM tracklist", db).set_index('id')

def get_genres():
    track_genres = track.merge(artist, left_on='artist_id', right_on='artist_id')[['track_id', 'genres']]
    playlist_genres = tracklist.merge(track_genres, on='track_id', how='outer')
    playlist_tracks = playlist_genres.groupby('playlist_id').agg(list)
    playlist_tracks.dropna()
    playlist_tracks['genres'] = playlist_tracks['genres'].apply(lambda genres: [genre.strip().replace("'", '') for genre in ",".join(genres).split(',') if isinstance(genre, str)])
    genres = pd.merge(playlist_tracks, playlist[['name', 'playlist_id']], on="playlist_id", how="left")
    return genres

def get_audio_features():
    audio_features = track.drop(['name', 'artist', 'artist_id'], axis=1)
    track_features = audio_features.merge(tracklist, on='track_id', how='outer').drop('track_id', axis=1)
    playlist_features = track_features.groupby('playlist_id', sort=False).median()
    playlist_features.drop(['key', 'liveness'], axis=1, inplace=True)
    return playlist_features

def get_genre_counts():
    genres = get_genres()
    all_genres = [genre for playlist_genres in genres['genres'] for genre in playlist_genres]
    counted = [pd.Series(playlist_genres).value_counts().to_dict() for playlist_genres in genres['genres']]
    genre_counts = genres.copy().drop('genres', axis=1).set_index('playlist_id')
    genre_counts['counted'] = counted
    gc = pd.json_normalize(genre_counts['counted'])
    gc = gc.fillna(0)
    gc = gc.astype(int)
    gc = gc.set_index(genres['playlist_id'])
    return gc

def feature_svd(features, n):
    svd = TruncatedSVD(n_components=n)
    X_reduced = svd.fit_transform(features)
    return X_reduced

def get_features():
    genre_counts = get_genre_counts()
    playlist_features = get_audio_features()
    features = genre_counts.join(playlist_features)
    for column in features.columns:
        features[column] = features[column] / features[column].abs().max()
    features = features.fillna(0)
    return features

def reduce_genres():
    genre_counts = get_genre_counts()
    X_reduced = feature_svd(genre_counts, 5)

def update_similarities():
    features = get_features()
    X_reduced = feature_svd(features, 2)

    similarity = cosine_similarity(X_reduced)
    np.fill_diagonal(similarity, -np.inf)

    max_cosine_similarities = [np.argpartition(row, -5)[-5:] for row in similarity]
    features = features.copy()
    features['max_cosine_similarity'] = max_cosine_similarities

    rec = pd.DataFrame(features['max_cosine_similarity'])
    rec = pd.merge(rec, playlist[['playlist_id', 'name']], on='playlist_id', how='left').set_index('name')

    rec['rec'] = rec['max_cosine_similarity'].apply(lambda x: [rec.iloc[i].name for i in x])
    rec.drop('max_cosine_similarity', axis=1, inplace=True)
    rec.reset_index()

    return rec

def get_recs(playlist_id):
    update_similarities()
    return rec_df.loc[rec_df['playlist_id'] == playlist_id, 'rec'].values[0]

rec_df = update_similarities()
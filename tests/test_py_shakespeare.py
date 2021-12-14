from py_shakespeare import py_shakespeare
import json
import pandas as pd
import requests
from nltk.tokenize import sent_tokenize, word_tokenize
from textstat.textstat import textstatistics,legacy_round
from bs4 import BeautifulSoup
import re
import pytest

@pytest.fixture
def toy_df_play():
    dict_answer = {'title': ["Julius Caesar", "Timon of Athens", "Henry VI, Part I"],
                   'popularity': ["High", "Medium", "Low"],
                   'genre' : ["Tragedy", "Tragedy", "History"],
                   'num_character' : [51,68, 63],
                   'play_length' : ["Low", "Low", "Low"],
                   'play_complexity' : ["High", "High", "High"]
                  }
    df = pd.DataFrame(dict_answer)
    return df

@pytest.fixture
def toy_df_monologue():
    dict_answer = {'play': ["hamlet", "romeo-and-juliet", "hamlet"],
                   'name': ["Hamlet", "Friar Lawrence", "The Ghost"],
                   'gender' : ["", "MALE", ""],
                   'degree' : [29, 18, 5],
                   'monologue_link' : ["http://www.folgerdigitaltexts.org/Ham/segment/sp-1639", "http://www.folgerdigitaltexts.org/Rom/segment/sp-1950", "http://www.folgerdigitaltexts.org/Ham/segment/sp-0767"],
                   'line_num' : [60, 51, 50]
                  }
    df = pd.DataFrame(dict_answer)
    return df


def test_shake_play(toy_df_play):
    ex_num_min_character = 40
    ex_play_complexity = "High"
    ex_play_length = "Low"
    pl = py_shakespeare.shake_play(min_num_character = ex_num_min_character, play_complexity = ex_play_complexity, play_length = ex_play_length)
    result = pl.get_summary()["title"]
    expected = toy_df_play["title"]
    assert result.equals(expected)
    
def test_shake_play_comp(toy_df_play):
    ex_num_min_character = 40
    ex_play_complexity = "High"
    ex_play_length = "Low"
    pl = py_shakespeare.shake_play(min_num_character = ex_num_min_character, play_complexity = ex_play_complexity, play_length = ex_play_length)
    result = pl.get_complete()["title"]
    expected = toy_df_play["title"]
    assert result.equals(expected)

    
def test_shake_monologue(toy_df_monologue):
    ex_gender = "ALL"
    ex_min_line = 50
    ex_include_all = False
    ex_play_list = ["Rom", "Ham"]
    ml = py_shakespeare.shake_monologue(gender = ex_gender, min_line = ex_min_line, include_all = ex_include_all, play_list = ex_play_list)
    result = ml.get_summary()["name"]
    expected = toy_df_monologue["name"]
    assert result.equals(expected) 
    
def test_shake_monologue_complex(toy_df_monologue):
    ex_gender = "ALL"
    ex_min_line = 50
    ex_include_all = False
    ex_play_list = ["Rom", "Ham"]
    ml = py_shakespeare.shake_monologue(gender = ex_gender, min_line = ex_min_line, include_all = ex_include_all, play_list = ex_play_list)
    result = ml.get_complexity()["name"]
    expected = toy_df_monologue["name"]
    assert result.equals(expected) 
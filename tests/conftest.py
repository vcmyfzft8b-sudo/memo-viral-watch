"""The code supports several markets; today only the Balkan one ('sh') is configured. Two stand-in markets ('fr',
'es') with their own language names let the tests keep checking the multi-market logic (group check, publishing)."""
from watcher.markets import TEXT

for _k, _name in (('fr', 'French'), ('es', 'Spanish')):
    TEXT.setdefault(_k, {**TEXT['sh'], 'lang_name': _name, 'codes': (_k,), 'names': (_name.lower(),), 'avoid_words': ''})

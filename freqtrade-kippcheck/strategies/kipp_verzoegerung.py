"""Variante C: identische SampleStrategy, aber jedes Einstiegs- und Ausstiegssignal kommt eine Kerze spaeter.
Sonst nichts geaendert."""
import importlib.util
from pathlib import Path
from pandas import DataFrame

_spec = importlib.util.spec_from_file_location("kipp_basis_sample", Path(__file__).with_name("sample_strategy.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

SIGNALE = ("enter_long", "enter_short", "exit_long", "exit_short")


class KippVerzoegerung(_mod.SampleStrategy):
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = super().populate_entry_trend(dataframe, metadata)
        for c in ("enter_long", "enter_short"):
            if c in df:
                df[c] = df[c].shift(1).fillna(0)
        if "enter_tag" in df:
            df["enter_tag"] = df["enter_tag"].shift(1)
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = super().populate_exit_trend(dataframe, metadata)
        for c in ("exit_long", "exit_short"):
            if c in df:
                df[c] = df[c].shift(1).fillna(0)
        if "exit_tag" in df:
            df["exit_tag"] = df["exit_tag"].shift(1)
        return df

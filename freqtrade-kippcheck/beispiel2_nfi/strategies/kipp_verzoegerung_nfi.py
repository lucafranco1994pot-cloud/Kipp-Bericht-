"""Variante C: NostalgiaForInfinityX8 unveraendert, aber Einstiegs-/Ausstiegs-SIGNALE eine Kerze spaeter.
(Eigene Ausstiegslogik von NFI wie custom_exit/Grinding bleibt unveraendert.)"""
import importlib.util
from pathlib import Path
from pandas import DataFrame

_spec = importlib.util.spec_from_file_location("kipp_basis_nfi_x8", Path(__file__).with_name("NostalgiaForInfinityX8.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class KippVerzoegerungNFI(_mod.NostalgiaForInfinityX8):
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

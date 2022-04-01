from typing import Callable, Optional

import rich
from anndata import AnnData
from mudata import MuData

from scvi._types import AnnOrMuData
from scvi.data.fields import AnnDataField, BaseAnnDataField


class BaseMuDataWrapper(BaseAnnDataField):
    def __init__(
        self, mod_key: Optional[str] = None, mod_required: bool = False
    ) -> None:
        super().__init__()
        if mod_required and mod_key is None:
            raise ValueError("Modality required for MuDataField but not provided.")
        self._mod_key = mod_key
        self._preregister = lambda _self, _mdata: None

    @property
    def adata_field(self) -> AnnDataField:
        return self._adata_field

    @property
    def registry_key(self) -> str:
        """The key that is referenced by models via a data loader."""
        return self.adata_field.registry_key

    @property
    def mod_key(self) -> Optional[str]:
        """The modality key of the data field within the MuData (if applicable)."""
        return self._mod_key

    @property
    def attr_name(self) -> str:
        """The name of the AnnData/MuData attribute where the data is stored."""
        return self.adata_field.attr_name

    @property
    def attr_key(self) -> Optional[str]:
        """The key of the data field within the relevant AnnData/MuData attribute."""
        return self.adata_field.attr_key

    @property
    def is_empty(self) -> bool:
        return self.adata_field.is_empty

    def get_modality(self, mdata: MuData) -> AnnOrMuData:
        if isinstance(mdata, AnnData):
            raise AssertionError("`get_modality` can only be called on MuData objects.")
        bdata = mdata
        if self.mod_key is not None:
            if self.mod_key not in mdata.mod:
                raise ValueError(f"Modality {self.mod_key} not found in mdata.mod.")
            bdata = mdata.mod[self.mod_key]
        return bdata

    def validate_field(self, mdata: MuData) -> None:
        bdata = self.get_modality(mdata)
        return self.adata_field.validate_field(bdata)

    def preregister(self, mdata: MuData) -> None:
        return self._preregister(self, mdata)

    def register_field(self, mdata: MuData) -> dict:
        self.preregister(mdata)
        bdata = self.get_modality(mdata)
        return self.adata_field.register_field(bdata)

    def transfer_field(
        self, state_registry: dict, mdata_target: MuData, **kwargs
    ) -> dict:
        bdata_target = self.get_modality(mdata_target)
        return self.adata_field.transfer_field(state_registry, bdata_target, **kwargs)

    def get_summary_stats(self, state_registry: dict) -> dict:
        return self.adata_field.get_summary_stats(state_registry)

    def view_state_registry(self, state_registry: dict) -> Optional[rich.table.Table]:
        return self.adata_field.view_state_registry(state_registry)


def MuDataWrapper(
    adata_field_cls: AnnDataField, preregister_fn: Optional[Callable] = None
) -> AnnDataField:
    if not isinstance(adata_field_cls, type):
        raise ValueError("`adata_field_cls` must be a class, not an instance.")

    def mudata_field_init(
        self, *args, mod_key: Optional[str] = None, mod_required: bool = False, **kwargs
    ):
        BaseMuDataWrapper.__init__(self, mod_key=mod_key, mod_required=mod_required)
        self._adata_field = adata_field_cls(*args, **kwargs)
        if preregister_fn is not None:
            self._preregister = preregister_fn

    return type(
        f"MuData{adata_field_cls.__name__}",
        (BaseMuDataWrapper,),
        {
            "__init__": mudata_field_init,
        },
    )

import os
from openpilot.common.params_pyx import Params as _NativeParams, ParamKeyFlag, ParamKeyType, UnknownKeyName
assert _NativeParams
assert ParamKeyFlag
assert ParamKeyType
assert UnknownKeyName

CUSTOM_DEFAULTS = {
  "FreePilotsVaultEnabled": True,
  "FreePilotsVaultUrl": "https://ddash.aaam.sa",
  "FreePilotsVaultToken": "freepilot_secret_token_2026",
}

DEFAULT_PARAMS_DIR = "/data/params/d"


class Params:
  def __init__(self, d: str = ""):
    self._native = _NativeParams(d) if d else _NativeParams()
    self._dir = os.path.join(d, "d") if d else DEFAULT_PARAMS_DIR

  def _read_disk(self, key: str) -> bytes | None:
    path = os.path.join(self._dir, key)
    try:
      with open(path, "rb") as f:
        return f.read()
    except Exception:
      return None

  def _write_disk(self, key: str, val_bytes: bytes) -> None:
    try:
      os.makedirs(self._dir, exist_ok=True)
      path = os.path.join(self._dir, key)
      with open(path, "wb") as f:
        f.write(val_bytes)
    except Exception:
      pass

  def check_key(self, key: str | bytes) -> bytes:
    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
    try:
      return self._native.check_key(key)
    except UnknownKeyName:
      if key_str in CUSTOM_DEFAULTS or key_str.startswith("FreePilots"):
        return key_str.encode("utf-8")
      raise

  def get(self, key: str | bytes, block: bool = False, return_default: bool = False, encoding: str | None = None) -> str | bytes | None:
    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
    try:
      val = self._native.get(key, block=block, return_default=return_default)
      if encoding and isinstance(val, bytes):
        return val.decode(encoding)
      return val
    except UnknownKeyName:
      raw = self._read_disk(key_str)
      if raw is None:
        def_val = CUSTOM_DEFAULTS.get(key_str)
        if return_default or def_val is not None:
          raw = str(def_val).encode("utf-8")
      if raw is None:
        return None
      if encoding:
        return raw.decode(encoding)
      return raw.decode("utf-8")

  def get_bool(self, key: str | bytes, block: bool = False) -> bool:
    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
    try:
      return self._native.get_bool(key, block=block)
    except UnknownKeyName:
      raw = self._read_disk(key_str)
      if raw is None:
        return bool(CUSTOM_DEFAULTS.get(key_str, False))
      return raw.strip() == b"1" or raw.strip().lower() == b"true"

  def put(self, key: str | bytes, dat: str | bytes, block: bool = False) -> int:
    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
    try:
      return self._native.put(key, dat, block=block)
    except UnknownKeyName:
      val_bytes = dat.encode("utf-8") if isinstance(dat, str) else dat
      self._write_disk(key_str, val_bytes)
      return 0

  def put_bool(self, key: str | bytes, val: bool, block: bool = False) -> int:
    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
    try:
      return self._native.put_bool(key, val, block=block)
    except UnknownKeyName:
      self._write_disk(key_str, b"1" if val else b"0")
      return 0

  def put_non_blocking(self, key: str | bytes, dat: str | bytes) -> int:
    return self.put(key, dat, block=False)

  def put_bool_non_blocking(self, key: str | bytes, val: bool) -> int:
    return self.put_bool(key, val, block=False)

  def remove(self, key: str | bytes) -> int:
    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
    try:
      return self._native.remove(key)
    except UnknownKeyName:
      try:
        os.remove(os.path.join(self._dir, key_str))
      except Exception:
        pass
      return 0

  def get_param_path(self, key: str = "") -> str:
    return os.path.join(self._dir, key)

  def clear_all(self, tx_flag=ParamKeyFlag.ALL) -> None:
    return self._native.clear_all(tx_flag)

  def all_keys(self, flag=ParamKeyFlag.ALL) -> list[str]:
    keys = list(self._native.all_keys(flag))
    for k in CUSTOM_DEFAULTS.keys():
      if k not in keys:
        keys.append(k)
    return keys

  def get_default_value(self, key: str | bytes) -> str | None:
    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
    try:
      return self._native.get_default_value(key)
    except UnknownKeyName:
      v = CUSTOM_DEFAULTS.get(key_str)
      return str(v) if v is not None else None

  def get_type(self, key: str | bytes) -> ParamKeyType:
    try:
      return self._native.get_type(key)
    except UnknownKeyName:
      return ParamKeyType.STRING

  def __getattr__(self, name: str):
    return getattr(self._native, name)


if __name__ == "__main__":
  import sys

  params = Params()
  test_key = sys.argv[1]
  assert params.check_key(test_key), f"unknown param: {test_key}"

  if len(sys.argv) == 3:
    val = sys.argv[2]
    print(f"SET: {test_key} = {val}")
    params.put(test_key, val, block=True)
  elif len(sys.argv) == 2:
    print(f"GET: {test_key} = {params.get(test_key)}")

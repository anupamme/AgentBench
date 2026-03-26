class FeatureFlags {
  constructor(defaults = {}) {
    this._flags = { ...defaults };
  }

  isEnabled(flag) {
    return Boolean(this._flags[flag]);
  }

  override(flag, value) {
    this._flags[flag] = value;
  }
}

module.exports = { FeatureFlags };

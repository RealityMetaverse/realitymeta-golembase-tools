export class RealityNFTError extends Error {
  constructor(message: string, public readonly code?: string) {
    super(message);
    this.name = "RealityNFTError";
  }
}

export class ConfigurationError extends RealityNFTError {
  constructor(message: string) {
    super(message, "CONFIGURATION_ERROR");
    this.name = "ConfigurationError";
  }
}

export class InitializationError extends RealityNFTError {
  constructor(message: string) {
    super(message, "INITIALIZATION_ERROR");
    this.name = "InitializationError";
  }
}

export class DataProcessingError extends RealityNFTError {
  constructor(message: string) {
    super(message, "DATA_PROCESSING_ERROR");
    this.name = "DataProcessingError";
  }
}

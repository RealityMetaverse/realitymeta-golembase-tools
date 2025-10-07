import { EntityType } from "./types";

export const SYSTEM_ANNOTATION_KEYS = {
  FILE_STEM: "_sys_file_stem",
  DATA: "_sys_data",
  COMPRESSION_METHOD: "_sys_compression_method",
  VERSION: "_sys_version",
  STATUS: "_sys_status",
  FILE_TYPE: "_sys_file_type",
  CATEGORY: "_sys_category",
} as const;

export const ATTRIBUTE_KEYS = {
  TYPE: "type",
  SETTLEMENT: "settlement",
  COUNTRY_NAME: "country_name",
} as const;

export const COMPRESSION_METHODS = {
  GZIP: "gzip",
} as const;

export const QUERY_STATUS_VALUES = {
  BOTH: "both",
  PROD: "prod",
} as const;

export const FILE_TYPE = {
  JSON: "json",
} as const;

export const ENTITY_TYPE_PRIORITY: EntityType[] = [
  EntityType.COUNTRY,
  EntityType.CITY,
  EntityType.BUILDING,
];

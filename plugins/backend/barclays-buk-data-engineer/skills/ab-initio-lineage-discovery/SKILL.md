---
name: ab-initio-lineage-discovery
description: >
    Generic domain knowledge for extracting end-to-end attribute-level lineage from any Ab Initio
    sandbox. Covers sandbox auto-discovery, DML parsing, graph (.mp) analysis, XFR transform
    patterns, RES/TWS schedule dependency walking, multi-source field attribution, data dictionary
    enrichment, transformation classification, confidence scoring, and 8-sheet workbook generation.
    Works with any Ab Initio project — not tied to a specific sandbox or domain.
user-invocable: false
status: approved
effective_date: 2026-09-01
owner: BUK Data Engineering Practice
---

## Important

This skill provides knowledge for EXTRACTING LINEAGE from Ab Initio artifacts. It does NOT execute Ab Initio graphs, connect to live databases or clusters, or modify existing graph files. It is used by the `ab-initio-discovery-agent` to analyse sandbox artifacts and produce lineage metadata.

The skill is **sandbox-agnostic** — it auto-discovers directory structure, file locations, environment variable prefixes, and source systems from whatever sandbox is provided. No hardcoded paths, table names, or domain assumptions.

---

## Ab Initio Sandbox Structure

Ab Initio projects use a sandbox directory layout. The exact subdirectory names vary by project.

### Auto-Discovery Algorithm

The agent does NOT assume fixed directory names. Instead it:

1. **Scan for `.mp` files**: `find <sandbox_root> -name "*.mp" -type f` — identifies graph directories
2. **Scan for `.dml` files**: `find <sandbox_root> -name "*.dml" -type f` — identifies DML directories
3. **Scan for `.xfr` files**: `find <sandbox_root> -name "*.xfr" -type f` — identifies transform directories
4. **Scan for `.ksh` files**: `find <sandbox_root> -name "*.ksh" -type f` — identifies run script directories
5. **Identify published DML path**: If a separate `pub_dml_path` is provided, use it. Otherwise search for DML files containing source table structures (tables referenced in graphs but not in the sandbox DML directory).

### Typical Layout (varies by project)

```
<sandbox_root>/
  <sandbox_name>/
    mp/                    <- Graph files (.mp), often in domain subdirectories
      <domain_1>/          <- e.g., CA/, CL/, BIV/ — varies by project
      <domain_2>/
    dml/                   <- Data Metadata Language files (.dml)
      <domain_1>/
    xfr/                   <- Transform files (.xfr)
    run/                   <- Shell scripts (.ksh) for graph execution
    sql/                   <- SQL scripts (optional)
    include/               <- Shared include files (optional)
    pset/                  <- Parameter set files (.pset) (optional)
```

A published DML directory may exist separately and contains:
- **Target/intermediate DMLs** — often in subdirectories by layer (e.g., BSL/, STG/, RAW/)
- **Source table DMLs** — one DML per external source table, named after the table

### File Types

| Extension | Purpose | Parsing Approach |
|---|---|---|
| `.mp` | Ab Initio graph (binary with embedded text) | grep/string extraction for DML refs, subgraph labels, field assignments, component types |
| `.dml` | Data Metadata Language — record structures | Regex parsing of record type blocks |
| `.xfr` | Transform files — reusable transformation logic | Text parsing for function signatures, switch/case, assignments |
| `.ksh` | Run scripts — execution wrappers | Parameter extraction, graph invocation commands |
| `.pset` | Parameter sets — runtime parameters | Key=value pairs for graph parameterisation |

---

## DML Parsing Rules

DML files define record structures with typed fields. The target DML defines the exact output schema.

### Record Structure

Ab Initio DMLs define typed records. The most common patterns:

```dml
type <record_type_name> =
record
  <datatype> <field_name> =NULL;
  <datatype> <field_name> =NULL;
  ...
end;
metadata type = <record_type_name>;
```

Common type names: `hive_row_t`, `record_type`, `output_type`, etc.
Partition types (to be skipped): `hive_partition_t`, `partition_type`, etc.

Include directives may appear: `include "/~ab_home/include/hive-types.dml";`

### Parsing Algorithm

1. **Identify the main record type**: Find the record block that feeds the `metadata type =` declaration. Skip partition record types.
2. **Enter record block** after `record` keyword.
3. **For each line**, apply regex: `^(.+?)\s+(\w+)\s*=\s*NULL\s*;?\s*$`
   - **Group 1** = full datatype (e.g., `big endian decimal(16,0,binary)`, `hive_string_t`, `hive_int_t`)
   - **Group 2** = attribute name (e.g., `mi_account_no`, `product_type`)
4. **Strip inline comments**: remove `//...` from end of line before matching.
5. **Stop** at `end;`.

### Skip Rules

- **Partition records**: Skip any record type containing `partition` in its name (between its type declaration and its `end;`)
- **Ab Initio system fields**: Skip `_AB_read_hdfs_files_starting_path_` and similar system-injected fields
- **Function definitions**: Skip lines containing `()` (e.g., `get_partition_fields()`, `hive_to_dml_version()`)
- **Duplicate names**: If the same attribute name appears in both partition and data record types, keep only the data record version

### Common Ab Initio Data Types

| DML Type Pattern | Meaning |
|---|---|
| `hive_string_t` | Variable-length string |
| `hive_int_t` | 32-bit integer |
| `hive_bigint_t` | 64-bit integer |
| `hive_double_t` | Double-precision float |
| `big endian decimal(p,s,binary)` | Fixed-precision decimal (p=precision, s=scale) |
| `string("delimiter")` | Delimited string |
| `integer(n)` | Fixed-width integer |
| `decimal("format")` | Formatted decimal |
| `date("format")` | Date with format pattern |
| `void` | Void/null type |

Note: Types vary by Ab Initio version and project configuration. Always extract the EXACT type string from the DML — do not normalise or simplify.

---

## Graph (.mp) Analysis

Ab Initio graph files are binary but contain embedded text metadata that can be extracted using standard text tools.

### Extracting DML References

```bash
grep -o '\$[A-Za-z_/]*\.dml' <graph_file>.mp | sort -u
```

Returns environment-variable-prefixed paths. The variable prefixes are project-specific (e.g., `$PROJ_DML/`, `$PUB_DML/`, `$AI_DML/`). The agent resolves these by:
1. Searching the sandbox and pub_dml_path for matching filenames
2. Using the basename of each path to locate the actual file

### Extracting XFR References

```bash
grep -o '\$[A-Za-z_/]*\.xfr' <graph_file>.mp | sort -u
```

### Identifying Subgraph Components

```bash
grep -o 'Subgraph created from graph "[^"]*"' <graph_file>.mp | sort -u
```

Extracts labelled subgraph component names. These help understand the graph's processing stages. Look for accompanying labels in the text near each subgraph declaration (typically within 200 characters after the subgraph line).

### Identifying Component Types

Search the `.mp` file for these markers:

| Marker | Component Type |
|---|---|
| `?join` | Join component |
| `join_type\|Inner Join` | Inner join |
| `join_type\|Full Outer Join` | Full outer join |
| `join_type\|Explicit` | Explicit (left/right outer) join |
| `Filter by Expression` | Filter component |
| `select_expr` | Filter expression |
| `Rollup` or `rollup` | Rollup/aggregation component |
| `sorted_input` | Sort requirement indicator |
| `Reformat` or `reformat` | Reformat/transform component |
| `Scan` or `scan` | Scan/read component |
| `Normalize` | Normalize component |
| `Denormalize` | Denormalize component |

### Extracting Field Assignments

Search for `out.<field> :: <expression>` patterns in the graph text:

```bash
grep -o 'out\.[a-zA-Z_][a-zA-Z0-9_]* :: [^|]*' <graph_file>.mp
```

These reveal which input port fields feed each output field:
- `out.field_a :: in0.field_a` → DIRECT_MAPPING (same name)
- `out.field_a :: in1.other_field` → RENAME (different source field name)
- `out.field_a :: if(in0.x >= 4 ...) 1 else 0` → DERIVATION (conditional logic)
- `out.field_a :: (decimal(""))in0.field_b` → DIRECT_MAPPING with type cast

---

## XFR Transform Patterns

XFR files contain reusable transformation logic referenced by graphs.

### Common Structure

```xfr
out :: finalize(temp, in) =
begin
  let <type> <var> = <init>;
  ...
  switch(<expression>)
  case <value>: begin ... end;
  case <value>: begin ... end;
  default: begin ... end;
  end;
end;
```

### Key Patterns to Extract

- **Function signature**: `out :: <function_name>(args)` — identifies the transform function
- **Switch/case blocks**: Conditional value mapping
- **Variable declarations**: `let <type> <name> = <value>;` — local computation variables
- **Parameter references**: `${PARAM_NAME}` — runtime parameters from pset files
- **For loops**: `for(var, condition)` — iterative processing
- **Nested begin/end blocks**: Complex multi-step logic

---

## RES / TWS Dependency Walking

RES (Release Engineering Specification) or TWS (Tivoli Workload Scheduler) sheets define job scheduling dependencies. These are the **authoritative source** for identifying upstream source systems.

### File Format

Schedule/job files are typically `.xlsm` (macro-enabled Excel) or `.xlsx` workbooks. The agent auto-discovers sheet names by scanning for sheets containing job and schedule definitions.

### Sheet Discovery Algorithm

The agent does NOT assume fixed sheet names. Instead:

1. **Load every `.xlsm` and `.xlsx`** file in the RES directory
2. **Scan sheet names** for patterns:
   - Job definitions: sheets containing `Job` AND (`PROD` or `Production`) in name
   - Schedule definitions: sheets containing `Schedule` or `Schdule` (common typo) AND (`PROD` or `Production`)
3. **Auto-detect column positions** by scanning header rows for keywords:
   - Job sheets: look for columns containing `JobName`, `Script`, `Parameters`, `Description`
   - Schedule sheets: look for columns containing `Reference`, `ScheduleName`, `JobNames`, `Dependencies`

### Dependency Format

Dependencies are comma-separated strings. Common patterns:

```
<job_name>                                    — job in same schedule
<workload>#<schedule>.<job>                   — cross-schedule dependency
<workload>#<schedule>                         — entire schedule dependency
```

Parse each item by splitting on `#` and `.`:
- If contains `#` and `.`: extract workload, schedule, job
- If contains `#` only: extract workload, schedule (find all jobs in that schedule)
- If plain string: job in the same schedule

### Recursive Walking Algorithm

```
function walk_deps(job_name, visited):
    if job_name in visited: return
    visited.add(job_name)
    
    info = lookup_schedule(job_name)
    job_detail = lookup_job(job_name)
    
    record(job_name, info, job_detail)
    
    for each dependency in parse_deps(info.deps):
        if dependency is a job_name:
            walk_deps(dependency, visited)
        elif dependency is a schedule:
            for each job in that schedule:
                walk_deps(job, visited)
```

### Identifying Source Database Extraction Jobs

A job extracts from an external database if its parameters or description match patterns such as:
- Parameters containing `/src_ext/`, `_unload`, `td_unload`, `extract`, `source`
- Description containing `Unload from`, `Extract from`, `Source extract`, `Load from`

The source table name is extracted from:
- **Job description**: e.g., `"Unload from <database> Table <TABLE_NAME>"` → extract `<TABLE_NAME>`
- **Parameter filename**: e.g., `<project>_td_unload_<TABLE_NAME>.pset` → extract the table name after the last recognisable prefix (`td_unload_`, `extract_`, `_unload_`, etc.)
- **Parameter path**: reverse-engineer from the pset filename by stripping known prefixes/suffixes

### Critical Rule: Validate Against the Tree

The RES dependency tree is the ONLY reliable way to determine actual source tables for a given graph. Do NOT assume a table is a source just because:
- A DML with that table name exists in the sandbox
- The field name matches a field in that table's DML
- It seems logical that the data would come from that table

A table can contain fields with the same names as those in another table. The RES tree tells you WHICH table actually feeds the pipeline.

---

## Multi-Source Field Attribution

When a target field is derived from fields in multiple source tables, ALL contributing sources must be recorded.

### Rules

1. List all source tables separated by `; ` in the `final_source_table` cell
2. List corresponding source attributes as `TABLE1.attr; TABLE2.attr` in `final_source_attribute` cell
3. Set transformation_type to `DERIVATION`
4. Add review comment: `Multi-source derivation: TABLE1; TABLE2; ...`

### How to Detect Multi-Source Fields

A field is multi-source when:
- The graph `out.field :: expression` references fields from multiple input ports (`in0.x`, `in1.y`)
- The field is derived from a conditional that evaluates fields originating from different source tables
- The field aggregates or combines data from joins of multiple upstream datasets

---

## Transformation Type Classification

| Type | Meaning | Evidence |
|---|---|---|
| `DIRECT_MAPPING` | Field passes through unchanged | Same field name in source and target DML; `out.field :: in.field` in graph |
| `RENAME` | Field name changes, no logic | `out.new_name :: in.old_name` where names differ |
| `DERIVATION` | Computed from source fields | `out.field :: if(...) ... else ...` conditional logic |
| `JOIN` | Populated via join to reference dataset | Join component in graph; field from non-primary input |
| `LOOKUP` | Populated via lookup component | Lookup join on key; balance/reference snapshot |
| `AGGREGATION` | Aggregate (MAX/MIN/SUM/COUNT) | Rollup component; aggregate function over group |
| `FILTER` | Values filtered by expression | Filter by Expression component |
| `CONDITIONAL_RULE` | IF/CASE/SWITCH logic | Explicit conditional in graph or XFR |
| `CONSTANT` | Hardcoded value or reserved filler | Filler fields, constant assignments |
| `SYSTEM_GENERATED` | Runtime parameters | Partition dates, processing timestamps from environment |
| `UNKNOWN` | Cannot be resolved | Flag for manual review |

---

## Confidence Scoring

| Score Range | Band | Evidence State | Criteria |
|---|---|---|---|
| 0.90 – 1.00 | HIGH | ESTIMATED | Direct mapping confirmed: field exists in source DML + graph assignment matches + RES confirms source table |
| 0.70 – 0.89 | MEDIUM | ESTIMATED | Derivation logic inferred: field exists in intermediate DML + graph component analysis suggests transformation |
| 0.40 – 0.69 | LOW | ASSUMED | Complex multi-source, logic unclear from available artifacts, or field not found in any input DML |

---

## Data Dictionary Enrichment

If a data dictionary file is provided, use it to add business context to each attribute.

### Auto-Detection

The agent looks for data dictionaries by:
1. Using the explicitly provided `--dictionary` path
2. Searching the sandbox/project root for files matching: `*Data Dictionary*.xlsx`, `*data_dictionary*.xlsx`, `*DataDictionary*.xlsx`

### Parsing

The dictionary is typically an `.xlsx` file with a main sheet (often named `Dictionary`, `Data Dictionary`, `Attributes`, or `Columns`). The agent auto-detects the header row by scanning for columns containing keywords like:
- `Database`, `Table`, `Attribute`, `Column`, `Field`
- `Format`, `Type`, `DataType`
- `Description`, `Definition`, `Meaning`
- `Source System`, `Source`, `Origin`

### Matching Rules

| Match Type | Algorithm |
|---|---|
| `EXACT` | Case-insensitive exact match on attribute/column name |
| `NORMALIZED` | Match after normalising: remove underscores, expand common abbreviations (`acc`→`account`, `num`→`number`, `dt`→`date`, `ind`→`indicator`, `amt`→`amount`, `bal`→`balance`, `cust`→`customer`, `acct`→`account`) |
| `INFERRED` | Semantic match based on business meaning (e.g., `deceased_date` may match `Deceased_Indicator`) |
| `NOT_IN_DICTIONARY` | No match found — field is likely pipeline-derived |

---

## Output Workbook Specification

The workbook contains 8 sheets with professional formatting (dark headers, white bold font, thin borders, wrap text).

### Sheet 1: Attribute_Mapping (27 columns)

One row per target attribute. Must match exact DML attribute count.

| Column | Description |
|---|---|
| target_dataset | Target dataset name |
| target_attribute | Attribute name from DML |
| target_datatype | Exact datatype from DML (e.g., `big endian decimal(16,0,binary)`) |
| attribute_definition | Business definition from Data Dictionary |
| business_definition | Business meaning |
| immediate_parent_dataset | Intermediate dataset(s) containing this field |
| immediate_parent_attribute | Field name in parent dataset |
| transformation_type | Classification (DIRECT_MAPPING, DERIVATION, etc.) |
| transformation_logic | Detailed transformation description |
| source_dataset | Source dataset(s) — may contain multiple separated by `; ` |
| source_attribute | Source field(s) — may contain `TABLE.field; TABLE.field` |
| final_source_system | Source system name(s) |
| final_source_database | Database name(s) |
| final_source_schema | Schema name(s) |
| final_source_table | Source table name(s) — multiple separated by `; ` |
| final_source_attribute | Source attribute(s) — multiple separated by `; ` |
| final_source_attribute_definition | Definition from Data Dictionary |
| lookup_datasets_used | Any lookup datasets used |
| join_datasets_used | Any join datasets used |
| business_rule | Business rule description |
| graph_name | Graph `.mp` filename |
| xfr_file | XFR filename if applicable |
| dml_file | Target DML filename |
| lineage_depth | Number of transformation levels from source to target |
| mapping_status | COMPLETED / PARTIAL / UNKNOWN |
| mapping_confidence | HIGH / MEDIUM / LOW |
| review_comments | Notes, multi-source details, manual review flags |

### Sheet 2: Lineage_Path (3 columns)

| Column | Description |
|---|---|
| target_attribute | Attribute name |
| lineage_path | Readable chain: `SOURCE.field -> intermediate -> graph -> TARGET.field` |
| lineage_depth | Number of levels |

### Sheet 3: Dataset_Lineage (5 columns)

| Column | Description |
|---|---|
| source_dataset | Source table/dataset with job reference |
| transformation_graph | Graph name that performs the transformation |
| intermediate_dataset | Intermediate dataset(s) in the pipeline |
| target_dataset | Final target dataset |
| business_purpose | What this source contributes |

### Sheet 4: Graph_Inventory (5 columns)

| Column | Description |
|---|---|
| graph_name | Graph `.mp` filename |
| graph_path | Full path to graph file |
| input_datasets | All input datasets (from DML references + RES) |
| output_datasets | All output datasets |
| business_purpose | Description of what the graph does |

### Sheet 5: XFR_Inventory (4 columns)

| Column | Description |
|---|---|
| xfr_name | XFR filename or inline transform description |
| graph_name | Graph using this transform |
| target_attribute | Attribute(s) produced |
| logic_summary | Summary of transformation logic |

### Sheet 6: Data_Dictionary_Matches (9 columns)

| Column | Description |
|---|---|
| attribute_name | Target attribute |
| dictionary_attribute_name | Matched dictionary entry |
| business_definition | Definition from dictionary |
| attribute_definition | Technical definition |
| data_type | Dictionary datatype |
| source_system | Source system from dictionary |
| business_entity | Business entity classification |
| match_type | EXACT / NORMALIZED / INFERRED / NOT_IN_DICTIONARY |
| confidence | Match confidence |

### Sheet 7: Business_Glossary (6 columns)

| Column | Description |
|---|---|
| attribute_name | Attribute name |
| business_definition | Short business term |
| attribute_description | Detailed description |
| source_system | Source system(s) |
| business_entity | Business entity |
| datasets_using_attribute | All datasets containing this attribute |

### Sheet 8: Source_System_Inventory (6 columns)

| Column | Description |
|---|---|
| source_system | System name |
| database | Database name |
| schema | Schema name |
| table | Table name |
| dataset | Intermediate dataset that reads from this table |
| attributes_used | List of attributes sourced from this table |

---

## OpenLineage Event Generation

### Event Structure

For each graph in the pipeline, generate a START + COMPLETE RunEvent pair:

```json
{
  "eventType": "COMPLETE",
  "eventTime": "<ISO-8601>",
  "run": {
    "runId": "<UUID>",
    "facets": {
      "processing_engine": {
        "_producer": "ab-initio-discovery-agent",
        "version": "1.0.0",
        "name": "Ab Initio"
      }
    }
  },
  "job": {
    "namespace": "<namespace>",
    "name": "<graph_name>",
    "facets": {
      "documentation": {
        "description": "<graph business purpose>"
      }
    }
  },
  "inputs": [
    {
      "namespace": "<namespace>",
      "name": "<source_dataset>",
      "facets": {
        "schema": {
          "fields": [
            {"name": "<field>", "type": "<type>"}
          ]
        }
      }
    }
  ],
  "outputs": [
    {
      "namespace": "<namespace>",
      "name": "<target_dataset>",
      "facets": {
        "schema": {
          "fields": [
            {"name": "<field>", "type": "<type>"}
          ]
        },
        "columnLineage": {
          "fields": {
            "<target_field>": {
              "inputFields": [
                {
                  "namespace": "<namespace>",
                  "name": "<source_dataset>",
                  "field": "<source_field>"
                }
              ],
              "transformationType": "<DIRECT_MAPPING|DERIVATION|...>",
              "transformationDescription": "<logic>"
            }
          }
        }
      }
    }
  ]
}
```

### Namespace Convention

If not provided, auto-generate: `<PROJECT>_<LAYER>_<DATASET_UPPER>_V1`

Where:
- `<PROJECT>` = derived from sandbox directory name
- `<LAYER>` = derived from DML subdirectory (e.g., BSL, STG, RAW)
- `<DATASET_UPPER>` = target dataset name in uppercase

### Job Naming

Graph `.mp` filename without extension.

### Safety Rules

1. All dataset names, column names, and map keys sanitised: dots replaced with underscores, brackets and `$` removed
2. No PII in lineage — only metadata (column names, types, transformation logic)
3. Events are idempotent — Marquez handles deduplication by runId

---

## Validation Checks

| ID | Check | Severity | Gate |
|---|---|---|---|
| V01 | All mappings have target_dataset populated | CRITICAL | Blocks upload |
| V02 | All mappings have target_attribute populated | CRITICAL | Blocks upload |
| V03 | All mappings have target_datatype matching DML | CRITICAL | Blocks upload |
| V04 | Attribute count in workbook matches DML attribute count | CRITICAL | Blocks upload |
| V05 | No dots/brackets/$ in sanitised OpenLineage keys | CRITICAL | Blocks upload |
| V06 | START/COMPLETE event pairs are balanced | CRITICAL | Blocks upload |
| V07 | All final_source_table values confirmed by RES dependency tree (if RES provided) | HIGH | Warning |
| V08 | No empty transformation_logic for DERIVATION type mappings | HIGH | Warning |
| V09 | Confidence scores are valid (HIGH/MEDIUM/LOW) | MEDIUM | Warning |
| V10 | Transformation types are valid enum values | MEDIUM | Warning |
| V11 | All multi-source attributes list ALL contributing tables | MEDIUM | Warning |
| V12 | OpenLineage JSON round-trip serialisation valid | CRITICAL | Blocks upload |
| V13 | All jobs in job_codes found in scheduling file (pipeline mode) | HIGH | Warning |
| V14 | Dependency matrix is acyclic (no circular dependencies) | HIGH | Warning |

---

## .project.pset Master Configuration Resolution

The `.project.pset` file at the sandbox root is the **master configuration** defining ALL environment variables for the project. It MUST be parsed FIRST before any other artifact analysis.

### Location

Found at: `<sandbox_root>/<sandbox_name>/.project.pset`

### Parsing Algorithm

1. **Identify key-value pairs**: Lines matching `<VARIABLE_NAME> = <value>` or `<VARIABLE_NAME> "<value>"`
2. **Resolve nested references**: Variables may reference other variables (e.g., `AI_DML = $PROJECT_DIR/dml`)
3. **Extract project identity**: Look for `AI_SYSTEM_NAME`, `AI_APPLICATION_NAME`, `AI_REL_LOC`
4. **Extract directory mappings**: `AI_BIN`, `AI_DML`, `AI_XFR`, `AI_DB`, `AI_SQL`, `AI_MP`, `AI_PSET`, `AI_RESOURCE`, `AI_RUN`/`RUN`
5. **Extract database config**: `TD_DB_HOME`, `TD_DB_DATA_SOURCE_NAME`, `TD_DB_HOST`, `TD_DB_DEFAULT`, `TD_DB_USER_NAME`
6. **Extract HDFS paths**: `AI_DATA_MOUNT`, `COMMON_9PSDM_HDFS_BSL_HOME`, `COMMON_9PSDM_HDFS_HOME`, `COMMON_9PSDM_HDMFS`
7. **Extract serial/lookup paths**: `AI_SERIAL_HOME`, `AI_SERIAL_BASE`, `AI_SERIAL_LOOKUP`
8. **Identify dependent projects**: Lines referencing other sandbox paths (e.g., `_Projects_BARCLAYS_9PSDM_common_9psdm_os`)

### Common Variable Patterns

| Variable | Typical Value | Purpose |
|---|---|---|
| `$AI_DML` | `$PROJECT_DIR/dml` | DML file directory |
| `$AI_XFR` | `$PROJECT_DIR/xfr` | Transform file directory |
| `$AI_MP` | `$PROJECT_DIR/mp` | Graph file directory |
| `$AI_PSET` | `$PROJECT_DIR/pset` | Parameter set directory |
| `$AI_BIN` | `$PROJECT_DIR/bin` | Script directory |
| `$AI_DB` | `$PROJECT_DIR/db` | Database connection directory |
| `$AI_SERIAL_LOOKUP` | `$AI_SERIAL_BASE/$AI_REL_LOC/lookup` | Lookup/config files |
| `$COMMON_9PSDM_HDFS_BSL_HOME` | `/tenant/bukw/projects/imp/databases` | HDFS database path |
| `$COMMON_9PSDM_HDMFS` | `$AI_DATA_MOUNT/hdmfs` | HDMFS staging path |

### Critical Rule

All environment variable references in DMLs, graphs, PSETs, and scripts (e.g., `$AI_DML/screening_common_types.dml`) must be resolved using this map before locating files.

---

## TWS Schedule File Parsing (Text Format)

TWS (Tivoli Workload Scheduler) scheduling definitions may be provided as plain-text dump files (e.g., `dumps_BDH`). These contain job schedules, dependencies, and execution scripts.

### File Format

```
SCHEDULE <WORKLOAD>#<SCHEDULE_NAME>
DESCRIPTION "<description>"
ON RUNCYCLE RULE1 "<frequency>"
AT <HHMM> [UNTIL <HHMM> +<N> DAYS ONUNTIL CANC]
[CARRYFORWARD]
[FOLLOWS <WORKLOAD>#<SCHEDULE>.<JOB> [PREVIOUS]]
[FOLLOWS <WORKLOAD>#<SCHEDULE>.@ [PREVIOUS]]
[LIMIT <N>]
:
<WORKLOAD>#<TASK_NAME>
 SCRIPTNAME "<script_path> <arguments>"
 STREAMLOGON <login>
 DESCRIPTION "<task_description>"
 TASKTYPE UNIX
 RECOVERY STOP
 [FOLLOWS <task_or_schedule_reference>]

END
```

### Parsing Algorithm

1. **Find SCHEDULE blocks**: Match `^SCHEDULE\s+(.+)$` to get schedule names
2. **Extract schedule metadata**: DESCRIPTION, ON RUNCYCLE (frequency), AT (start time), CARRYFORWARD, LIMIT
3. **Extract schedule-level dependencies**: `FOLLOWS` before the `:` separator are schedule-level dependencies
4. **Find task blocks**: After `:`, each `<WORKLOAD>#<TASK_NAME>` starts a task
5. **Extract task metadata**: SCRIPTNAME (path + args), STREAMLOGON, DESCRIPTION, TASKTYPE, RECOVERY
6. **Extract task-level dependencies**: `FOLLOWS` within a task block are task-level dependencies
7. **Parse FOLLOWS syntax**:
   - `<WORKLOAD>#<SCHEDULE>.<TASK>` — specific task in another schedule
   - `<WORKLOAD>#<SCHEDULE>.@` — ALL tasks in another schedule
   - `<TASK_NAME>` (plain) — task in same schedule
   - `PREVIOUS` suffix — depends on previous run of the same schedule
8. **Extract SCRIPTNAME components**: Path to wrapper script + argument (PSET or MP filename)

### Dependency Pattern Examples

```
FOLLOWS BDH_BUK_BIW2PROD#PBDHETLIMPSCDTCT.@          → All tasks in DTCT schedule
FOLLOWS BDH_BUK_BIW2PROD#PBDHETLIMPSCRPST.ETLIMPSCRPSTPRC  → Specific task
FOLLOWS GBRCSR00034_85#PETLTCGMSS.ETLTCGMSSCONTMFT    → Cross-workload dependency
FOLLOWS BDH_BUK_BIW2PROD#PBDHETLIMPSCDTCT.@ PREVIOUS  → Previous run only
```

### Key Extraction Fields

For each job, extract and record:
- **Schedule name** and **task name(s)**
- **Execution script** (from SCRIPTNAME — identifies the graph/PSET)
- **Start time** (from AT) and **frequency** (from ON RUNCYCLE)
- **Carry-forward window** (UNTIL + days)
- **All upstream dependencies** (from FOLLOWS)
- **StreamLogon** (service account)

---

## PSET Prototype Resolution

Ab Initio PSET files may serve two roles:
1. **Parameter sets** — simple key=value runtime parameters
2. **Plan definitions** — reference a prototype graph via `!prototype` and provide parameters for its execution

### Prototype Pattern

```pset
!prototype $COMMON_9PSDM_MP/bsl/psdm_bsl_cdc.mp
ANP_CURR_BUS_DTE "20260101"
ANP_PREV_BUS_DTE "20251231"
INPUT_DML "$AI_DML/gmss_screening_contequiv_output_file.dml"
INPUT_FILE_NAME "tcvcust_contequiv"
DELTA_KEY "{cont_equiv_id;}"
```

### Parsing Algorithm

1. **Check for `!prototype`**: If present, this PSET defines a plan execution, not just parameters
2. **Extract prototype path**: The graph referenced after `!prototype` is the actual execution graph
3. **Resolve the prototype graph path**: Use `.project.pset` environment variables to locate the actual file
4. **Extract all parameters**: Key-value pairs below the prototype declaration
5. **Identify CDC-specific parameters**: `DELTA_KEY`, `EXCLUDE_FROM_CDC_COMPARISON`, `DATA_TYPE`, `STANDARD_CDC_LOGIC`, `DEDUP_CHECK`
6. **Trace to input/output DMLs**: Parameters like `INPUT_DML`, `OUTPUT_DML`, `PREV_FILE`, `ARCHIVE_DIR`
7. **Extract date control**: Parameters referencing date control files (`.ctrl` files with pipe-delimited dates)

### Common PSET Parameter Patterns

| Parameter | Purpose |
|---|---|
| `!prototype` | Path to the framework graph being parameterized |
| `ANP_CURR_BUS_DTE` / `ANP_PREV_BUS_DTE` | Business dates (often from control files) |
| `INPUT_DML` / `OUTPUT_DML` | DML files defining input/output schemas |
| `INPUT_FILE_NAME` / `INPUT_FILE_PTRN` | Input file names or patterns |
| `DELTA_KEY` | CDC comparison key fields (e.g., `{cont_equiv_id;}`) |
| `EXCLUDE_FROM_CDC_COMPARISON` | Fields excluded from CDC comparison |
| `DATA_TYPE` | CDC type (e.g., `Key_with_Indicator`) |
| `STANDARD_CDC_LOGIC` | Y/N for standard CDC processing |
| `PREV_FILE` / `ARCHIVE_DIR` / `REJECT_DIR` | Previous snapshot, archive, and reject paths |
| `DT_CNTRL_FILE` | Date control file path |
| `HOLIDAY_CALENDAR_FILE` | Holiday calendar for date advancement |

---

## Wrapper Script Analysis

Many Ab Initio environments use a common wrapper script that is the universal entry point for all graph/PSET executions.

### Common Wrapper Pattern (e.g., `psdm_bsl_wrapper.ksh`)

The wrapper script typically:

1. **Accepts 1 argument**: The `.pset` or `.mp` filename to execute
2. **Locates sandbox**: `air sandbox find $JOB`
3. **Sources project setup**: `. ${SANDBOX}/ab_project_setup.ksh ${SANDBOX}`
4. **Authenticates**: Kerberos (`kinit -kt /apps/abinitio/keytabs/${USER}.keytab ${USER}@<REALM>`)
5. **Determines execution mode**: Plan (PSET with `!prototype...plan`) vs. Graph (MP)
6. **Executes**: `air sandbox run` with parameters
7. **Handles errors**: Auto-retry on YARN errors (configurable via lookup files)
8. **Post-execution**: MSCK REPAIR TABLE, Impala REFRESH/COMPUTE STATS, run statistics

### Key Elements to Extract

| Element | Where Found | Purpose |
|---|---|---|
| `AB_REPORT` | Environment variable | Monitoring frequency |
| `AI_ADMIN_LOG` / `AI_ADMIN_ERROR` | Environment variable | Log/error directories |
| `BEELINE_CONNECT_STRING` | Environment variable | Hive Beeline JDBC connection |
| `IMPALA_CONNECT_STRING` | Environment variable | Impala connection |
| `UNISON_SCHED` / `UNISON_JOB` | Environment variable | TWS schedule/job identifiers |
| Auto-rerun config | `bsl_auto_rerun_job_list.txt` | Jobs eligible for YARN error retry |
| Error patterns | `error_messages_for_rerun.lkp` | Patterns triggering auto-retry |
| MSCK repair list | `bsl_imp_bdr_trigger_list.lkp` | Tables requiring MSCK REPAIR + stats |
| Business date resolution | Multiple param names tried in order | CURR_BUS_DT, CURR_DT, etc. |

### Auto-Retry Pattern

```
Retry up to 4 times on YARN errors:
  - Retries 1-2: sleep 5 minutes
  - Retries 3-4: sleep 10 minutes
Error patterns matched against error_messages_for_rerun.lkp
```

---

## MFT Script Analysis

MFT (Managed File Transfer) scripts handle outbound file delivery to external systems. Two primary tools are used:

### Daffy (send2Dfe.sh)

```bash
/apps/daffy/dfe/bin/send2Dfe.sh -m single -j <JOB_CARD> -c <CONFIG_FILE> -f <FILE_PATH>
```

Key elements to extract:
- **Destination system** (from config/job card names)
- **File patterns** (what files are transferred)
- **Post-transfer actions** (gzip, archive, trigger file creation)
- **Dual job cards** (CDH/BDH for parallel delivery to two environments)

### Connect:Direct

```bash
<script>.sh <PROCESS_NAME> <SOURCE_DIR> <FILE_PATTERN> <SNODE_ID> <DEST_ID>
```

Key elements to extract:
- **Process name** (e.g., `M9616POD`)
- **Source/destination paths**
- **SNODE_ID** and **DEST_ID** per file
- **Transfer type** (binary/text)

### Common MFT Pattern Elements

| Element | Purpose |
|---|---|
| Trigger files (`.trg`, `.done`) | Signal completion to downstream systems |
| Archive after transfer | gzip + move to archive/ subdirectory |
| Housekeeping | Retention periods for trigger (4 days), logs (10 days), errors (10 days) |
| Dual CDH/BDH delivery | Transfers to both CDH and BDH environments independently |

---

## DBC File Parsing (Database Connections)

Ab Initio DBC files (`.dbc`) define database connection parameters.

### File Format

```dbc
[Connection]
type|Teradata
database|${DATABASE_NAME}
logtable_database|${TD_DB_LOG}
worktable_database|${TD_DB_WORK}
errortable_database|${TD_DB_ERROR}
character_set|ASCII
[End]
```

### Parsing Algorithm

1. **Extract DBMS type**: Line containing `type|<DBMS>` (e.g., `Teradata`, `Oracle`, `Hive`)
2. **Extract databases**: `database|<value>`, `logtable_database|<value>`, `worktable_database|<value>`, `errortable_database|<value>`
3. **Extract character set**: `character_set|<value>`
4. **Resolve variables**: Database values may reference environment variables from `.project.pset`

### Connection Details for Infrastructure Sheet

Cross-reference DBC files with `.project.pset` to resolve:
- **Host**: `TD_DB_HOST` variable
- **Database name**: `TD_DB_NAME` / `TD_DB_DATA_SOURCE_NAME`
- **Schema**: `TD_DB_DEFAULT`
- **User**: `TD_DB_USER_NAME`
- **Client version**: `TD_DB_HOME`

---

## Extended DML Parsing Rules

### Multi-Record-Type DMLs

Some DMLs define multiple record types in a single file using a union/switch pattern:

```dml
type hdr_rec_t =
record
  string(",") rec_type;
  string(",") creation_date;
end;

type bdy_rec_t =
record
  string(",") rec_type;
  string(",") customer_id;
  string(",") name;
end;

type trl_rec_t =
record
  string(",") rec_type;
  string(",") record_count;
end;

type input_layout_t =
record
  hdr_rec_t hdr;
  bdy_rec_t bdy;
  trl_rec_t trl;
end;
```

**Parsing rule**: When a DML contains multiple `record` blocks, identify the composite type (usually the one referenced by `metadata type =` or the one that contains other record types as fields). Extract fields from all constituent types.

### Additional Hive Type Patterns

| DML Type | Meaning |
|---|---|
| `hive_dml_timestamp_t` | Hive timestamp type |
| `hive_date_t` | Hive date type |
| `hive_float_t` | Hive float type |
| `hive_boolean_t` | Hive boolean type |
| `hive_binary_t` | Hive binary type |

### Partition Type Handling

DMLs for Hive tables often include a separate partition record type:

```dml
type hive_partition_t =
record
  hive_string_t dw_bus_date;
end;
```

**Rule**: Always skip partition record types when extracting the data schema. Identify partition fields separately and mark them with `PARTITION` designation in the workbook.

---

## Extended Graph (.mp) Analysis

### Additional Component Types

| Marker | Component Type | Description |
|---|---|---|
| `Read_HDFS` or `read_hdfs` | HDFS Read | Reads from HDFS/Hive (Parquet, ORC, text) |
| `Write_HDFS` or `write_hdfs` | HDFS Write | Writes to HDFS/Hive |
| `Write_Multiple_Files` | Multi-File Writer | Writes separate files per key |
| `Read_Multiple_Files` | Multi-File Reader | Reads files matching a pattern |
| `Partition_by_Key` | Partitioner | Hash/range partitioning |
| `Partition_by_Expression` | Expression Router | Routes records by expression evaluation |
| `Scan_with_Rollup` | Block Builder | Creates block-compressed output |
| `Gather` | Gatherer | Combines multiple input streams |
| `Concatenate` | Concatenator | Appends streams end-to-end |
| `Replicate` | Replicator | Copies input to multiple outputs |
| `Merge` | Merger | Merges sorted inputs |
| `Create_Data` | Data Generator | Generates records (e.g., file listings via `directory_listing`) |
| `Run_Program` | External Program | Executes shell commands (mv, gunzip, ls, etc.) |
| `Send_Mail` | Email Notification | Sends email alerts |
| `Fuse` | Fuser | Combines H/B/T records into ordered stream |

### Subgraph Pattern Recognition

Common subgraph patterns in Ab Initio graphs:

| Subgraph Name Pattern | Purpose |
|---|---|
| `Read_Hive_Table` / `Read_HDFS` | Hive/HDFS source read |
| `Write_HDFS` / `Loader` | HDFS/Hive target write |
| `gunzip` / `Decompress` | File decompression |
| `Combine HDR & TRL into Body` | H/B/T file assembly |
| `Audit Processing` | Audit file generation |
| `Move files to ARCHIVE` | Post-processing archival |
| `Send_Mail` | Email notification |
| `Recon Check` / `Reconciliation` | Record count validation |

---

## Pipeline Discovery Workbook Specification

When operating in pipeline mode, produce a 7-sheet workbook tailored for multi-job analysis.

### Sheet 1: Pipeline_Inventory

| Column | Description |
|---|---|
| Sr_No | Sequential number |
| Schedule_Name | Full TWS schedule name (e.g., `BDH_BUK_BIW2PROD#PBXXXXXXXXXXXXXX`) |
| Job_Code | Short job code |
| Task_Names | Task(s) within the schedule (semicolon-separated) |
| Description | Job purpose description |
| Graph_Script | Graph (.mp) or PSET (.pset) or script (.ksh) executed |
| Frequency | DAILY, WEEKLY, MONTHLY, etc. |
| Start_Time | Scheduled start time (HH:MM) |
| Carry_Forward | Carry-forward window (e.g., "5 days") |
| Dependencies | Upstream dependencies (semicolon-separated) |
| StreamLogon | Service account |
| Technology | Ab Initio Graph / PSET / KSH / MFT |

### Sheet 2: Source_Target_Mapping

| Column | Description |
|---|---|
| Mapping_ID | Unique identifier (STM-001, STM-002, ...) |
| Job_Code | Which job performs this mapping |
| Job_Name | Human-readable job name |
| Source_Dataset | Source dataset/file name |
| Source_Type | File, HDFS/Parquet, Teradata, MFT, etc. |
| Source_Namespace | Source location/database |
| Target_Dataset | Target dataset/file name |
| Target_Type | File, Hive/HDFS Parquet, MFT, etc. |
| Target_Namespace | Target location/database |
| Transformation_Type | DIRECT, FILTER, CDC, DERIVATION, LOOKUP_JOIN, MERGE_JOIN, TRANSFER |
| Description | What this mapping does |
| DML_File | Associated DML file(s) |
| Confidence | 0.0–1.0 score |

### Sheet 3: Column_Level_Lineage

| Column | Description |
|---|---|
| Mapping_ID | Unique identifier (CLL-001, CLL-002, ...) |
| Job | Which job performs this mapping |
| Source_Dataset | Source dataset name |
| Source_Column | Source column/field name |
| Source_Type | Source datatype |
| Target_Dataset | Target dataset name |
| Target_Column | Target column/field name |
| Target_Type | Target datatype |
| Transformation_Type | DIRECT, DERIVATION, RENAME, CDC, etc. |
| Transformation_Logic | Detailed transformation description |
| Confidence | 0.0–1.0 score |

### Sheet 4: Transformation_Catalog

| Column | Description |
|---|---|
| Transform_ID | Unique identifier |
| Job | Which job uses this transform |
| Component_Type | XFR, Reformat, Join, Filter, Rollup, CDC, MFT, Run_Program |
| Component_Name | Transform name from graph or file |
| Source_File | XFR/graph file containing the logic |
| Input_DML | Input DML type(s) |
| Output_DML | Output DML type(s) |
| Logic_Description | Detailed transformation logic |
| Validated_From | Evidence source (Code analysis, PSET file, Lineage document) |

### Sheet 5: Dependency_Matrix

A cross-tabulation matrix where:
- **Rows** = downstream jobs
- **Columns** = upstream jobs + external dependencies
- **Cells** = `YES (.@)`, `YES (.TASKNAME)`, `PREVIOUS`, `—` (no dependency)

### Sheet 6: Data_Quality_Rules

| Column | Description |
|---|---|
| Rule_ID | Unique identifier (DQ-001, DQ-002, ...) |
| Job | Which job applies this rule |
| Rule_Source | XFR file, graph component, or reconciliation check |
| Rule_Type | HEADER, TRAILER, RECORD, FILE_STRUCTURE, RECONCILIATION, USER, CDC_INTEGRITY |
| Fields | Field(s) being validated |
| Validation_Logic | Exact validation expression/condition |
| Action_On_Failure | What happens when validation fails |
| Severity | CRITICAL, HIGH, MEDIUM |

### Sheet 7: Infrastructure

| Column | Description |
|---|---|
| Component_ID | Unique identifier |
| Category | Scheduler, Database, File Storage, MFT, External System, Configuration, Trigger |
| Name | Component name |
| Details | Technical details |
| Used_By_Jobs | Which jobs use this component |
| Connection_Info | Connection string, host, path, or configuration details |

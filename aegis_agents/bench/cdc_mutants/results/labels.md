| Design | Mutant | CDC-safe (GT) | Sim-equiv (GT) | Lint | Sim | EQY | Structural CDC | Contract |
|---|---|---|---|---|---|---|---|---|
| async_fifo | binary_cross__x_753d5e36 | False | True | pass | pass | FAIL | **FLAG** | **FLAG** |
| async_fifo | binary_cross__x_cf11da04 | False | True | pass | pass | FAIL | **FLAG** | **FLAG** |
| async_fifo | extra_stage__x_753d5e36 | True | False | pass | pass | FAIL | pass | pass |
| async_fifo | extra_stage__x_cf11da04 | True | False | pass | pass | FAIL | pass | pass |
| async_fifo | free_dblinv_0 | True | True | pass | pass | PASS | pass | pass |
| async_fifo | free_dblinv_1 | True | True | pass | pass | FAIL | pass | pass |
| async_fifo | identity | True | True | pass | pass | PASS | pass | pass |
| async_fifo | post_invert__x_753d5e36 | True | False | pass | pass | FAIL | pass | pass |
| async_fifo | post_invert__x_cf11da04 | True | False | pass | **FLAG** (812) | FAIL | pass | pass |
| async_fifo | sync_bypass__x_753d5e36 | False | False | pass | **FLAG** (4) | FAIL | **FLAG** | **FLAG** |
| async_fifo | sync_bypass__x_cf11da04 | False | False | pass | **FLAG** (2) | FAIL | **FLAG** | **FLAG** |
| async_fifo | sync_remove__x_753d5e36 | False | False | pass | **FLAG** (8) | FAIL | **FLAG** | **FLAG** |
| async_fifo | sync_remove__x_cf11da04 | False | False | pass | **FLAG** (64) | FAIL | **FLAG** | **FLAG** |

| Operator | n | CDC-safe | Sim flags | EQY flags | Structural flags | Contract flags | Any CDC checker |
|---|---|---|---|---|---|---|---|
| binary_cross | 2 | False | 0 | 2 | 2 | 2 | 2 |
| extra_stage | 2 | True | 0 | 2 | 0 | 0 | 0 |
| free_dblinv | 2 | True | 0 | 1 | 0 | 0 | 0 |
| identity | 1 | True | 0 | 0 | 0 | 0 | 0 |
| post_invert | 2 | True | 1 | 2 | 0 | 0 | 0 |
| sync_bypass | 2 | False | 2 | 2 | 2 | 2 | 2 |
| sync_remove | 2 | False | 2 | 2 | 2 | 2 | 2 |

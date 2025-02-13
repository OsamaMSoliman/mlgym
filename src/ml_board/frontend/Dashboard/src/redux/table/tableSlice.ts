import { createEntityAdapter, createSlice, EntityState } from "@reduxjs/toolkit";
import { RootState } from "../store";


// NOTE: Row = JobStatusPayload + ExperimentStatusPayload + scores
export interface Row {
    // // Job
    // job_id?: string; // format <grid_search_id>-<job index>
    // job_type?: string; // <CALC, TERMINATE>
    // job_status?: string; // <INIT, RUNNING, DONE>
    // starting_time?: number;
    // finishing_time?: number;
    // error?: string;
    // stacktrace?: string;
    // device?: string;
    // // Experiment
    experiment_id: number;
    // model_status?: string;   // <TRAINING, EVALUATING>,
    // current_split?: string;
    // splits?: string; //e.g.: ["train", "val", "test"],
    // num_epochs?: number;
    // current_epoch?: number;
    // num_batches?: number;
    // current_batch?: number;
    // // progresses calculations
    // epoch_progress?: number;
    // batch_progress?: number;
    // // special Experiment keys for "latest_split_metric"


    // NOTE: newKey encompasses all of the above and more if need be!!!
    // [newKey: string]: number | string;
    // But unfortunately it creates errors if used! (exposing only experiment_id is the current fix)
}

const rowsAdapter = createEntityAdapter<Row>({
    selectId: ({ experiment_id }: Row) => experiment_id,
    sortComparer: ({ experiment_id: id1 }: Row, { experiment_id: id2 }: Row) => id1 - id2
});

// interface RowsState {
//     // The unique IDs of each Row.
//     ids: [];
//     // A lookup table mapping Rows' IDs to the corresponding Row objects
//     entities: {};
// }

const initialState: EntityState<Row> = rowsAdapter.getInitialState({});

export const tableSlice = createSlice({
    name: 'table',
    initialState,
    reducers: {
        upsertOneRow: rowsAdapter.upsertOne,
        upsertManyRows: rowsAdapter.upsertMany,
    }
});


export const { upsertOneRow, upsertManyRows } = tableSlice.actions;

// create a set of memoized selectors
export const {
    selectAll: selectAllRows,
    selectById: selectRowById
} = rowsAdapter.getSelectors((state: RootState) => state.table)

export default tableSlice.reducer;
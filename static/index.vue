<template id="page-lnpos">
  <div class="row q-col-gutter-md">
    <div class="col-12 col-md-7 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <q-btn
            unelevated
            color="primary"
            :label="$t('lnpos.new_lnpos')"
            @click="formDialog.show = true"
          ></q-btn>
        </q-card-section>
      </q-card>

      <q-card>
        <q-card-section>
          <div class="row items-center no-wrap q-mb-md">
            <div class="col">
              <h5
                class="text-subtitle1 q-my-none"
                v-text="$t('lnpos.lnpos_title')"
              ></h5>
            </div>

            <div class="col-auto">
              <q-input
                borderless
                dense
                debounce="300"
                v-model="filter"
                :placeholder="$t('lnpos.search')"
              >
                <template v-slot:append>
                  <q-icon name="search"></q-icon>
                </template>
              </q-input>
              <q-btn
                flat
                color="grey"
                @click="exportCSV"
                v-text="$t('lnpos.export_csv')"
              ></q-btn>
            </div>
          </div>
          <q-table
            flat
            dense
            :rows="lnposs"
            row-key="id"
            :columns="lnposColumns"
            v-model:pagination="lnposTable.pagination"
            :filter="filter"
          >
            <template v-slot:header="props">
              <q-tr :props="props">
                <q-th style="width: 5%"></q-th>
                <q-th style="width: 5%"></q-th>
                <q-th style="width: 5%"></q-th>
                <q-th
                  v-for="col in props.cols"
                  :key="col.name"
                  :props="props"
                  auto-width
                >
                  <div v-if="col.name != 'id'" v-text="col.label"></div>
                </q-th>
              </q-tr>
            </template>

            <template v-slot:body="props">
              <q-tr :props="props">
                <q-td>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="openUpdateLnpos(props.row.id)"
                    icon="edit"
                    color="blue"
                  >
                    <q-tooltip v-text="$t('lnpos.edit_lnpos')"></q-tooltip>
                  </q-btn>
                </q-td>
                <q-td>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="deleteLnpos(props.row.id)"
                    icon="cancel"
                    color="pink"
                  >
                    <q-tooltip v-text="$t('lnpos.delete_lnpos')"></q-tooltip>
                  </q-btn>
                </q-td>
                <q-td>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="copyDeviceString(props.row.id)"
                    icon="perm_data_setting"
                    color="primary"
                  >
                    <q-tooltip v-text="$t('lnpos.device_string')"></q-tooltip>
                  </q-btn>
                </q-td>
                <q-td
                  v-for="col in props.cols"
                  :key="col.name"
                  :props="props"
                  auto-width
                >
                  <div v-if="col.name != 'id'" v-text="col.value"></div>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </div>

    <div class="col-12 col-md-5 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <h6
            class="text-subtitle1 q-my-none"
            v-text="$t('lnpos.extension_title')"
          ></h6>
        </q-card-section>
        <q-separator></q-separator>
        <q-card-section>
          <p>
            <span v-text="$t('lnpos.extension_desc')"></span><br />
            LNPoS:
            <a class="text-secondary" href="https://lnbits.github.io/lnpos">
              https://lnbits.github.io/lnpos</a
            ><br />
          </p>
        </q-card-section>
      </q-card>
    </div>

    <q-dialog
      v-model="formDialog.show"
      deviceition="top"
      @hide="closeFormDialog"
    >
      <q-card class="q-pa-lg q-pt-xl lnbits__dialog-card">
        <q-form @submit="sendFormData" class="q-gutter-md">
          <h5 v-html="formDialog.data.device" v-if="formDialog.data.id"></h5>
          <q-input
            filled
            dense
            v-model.trim="formDialog.data.title"
            type="text"
            :label="$t('lnpos.title_label')"
          ></q-input>
          <q-select
            filled
            dense
            emit-value
            v-model="formDialog.data.wallet"
            :options="g.user.walletOptions"
            :label="$t('lnpos.wallet_label')"
          ></q-select>
          <q-select
            filled
            dense
            v-model.trim="formDialog.data.currency"
            type="text"
            :label="$t('lnpos.currency_label')"
            :options="currencies"
          ></q-select>
          <q-input
            filled
            dense
            v-model.trim="formDialog.data.profit"
            type="number"
            max="90"
            :label="$t('lnpos.profit_label')"
          ></q-input>
          <div class="row q-mt-lg">
            <q-btn
              v-if="formDialog.data.id"
              unelevated
              color="primary"
              :disable="formDialog.data.title == ''"
              type="submit"
              :label="$t('lnpos.update_lnpos')"
            ></q-btn>
            <q-btn
              v-else
              unelevated
              color="primary"
              :disable="formDialog.data.title == ''"
              type="submit"
              :label="$t('lnpos.create_lnpos')"
            ></q-btn>
            <q-btn
              @click="cancelLnpos"
              flat
              color="grey"
              class="q-ml-auto"
              :label="$t('lnpos.cancel')"
            ></q-btn>
          </div>
        </q-form>
      </q-card>
    </q-dialog>
  </div>
</template>

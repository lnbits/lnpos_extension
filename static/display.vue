<template id="page-lnpos-public">
  <div class="row q-col-gutter-md justify-center">
    <div class="col-12 col-md-7 col-lg-6 q-gutter-y-md">
      <q-card class="q-pa-lg">
        <q-card-section class="q-pa-none">
          <div class="text-center">
            <div v-if="loading">
              <q-spinner-dots size="3rem"></q-spinner-dots>
            </div>
            <div v-else-if="paid">
              <h3 class="q-my-none" v-text="pin"></h3>
            </div>
            <div v-else>
              <h3 class="q-my-none">LNURL-pay not paid</h3>
              <br />
              <q-icon
                name="warning"
                class="text-grey"
                style="font-size: 20rem"
              ></q-icon>
              <br />
            </div>
          </div>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>

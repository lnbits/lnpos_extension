window.PageLnposPublic = {
  template: '#page-lnpos-public',
  data() {
    return {
      loading: true,
      paid: false,
      pin: null
    }
  },
  methods: {
    getPaymentStatus() {
      LNbits.api
        .request(
          'GET',
          `/lnpos/api/v1/payment/${this.$route.params.payment_id}`
        )
        .then(response => {
          this.paid = response.data.paid
          this.pin = response.data.pin
          this.loading = false
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
          this.loading = false
        })
    }
  },
  created() {
    this.getPaymentStatus()
  }
}

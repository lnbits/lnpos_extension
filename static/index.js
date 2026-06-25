window.PageLnpos = {
  template: '#page-lnpos',
  computed: {
    currencies() {
      if (this.g.allowedCurrencies && this.g.allowedCurrencies.length > 0) {
        return ['sat', ...this.g.allowedCurrencies]
      } else {
        return ['sat', ...(this.g.currencies || [])]
      }
    },
    lnposColumns() {
      return [
        {
          name: 'title',
          align: 'left',
          label: this.$t('lnpos.col_title'),
          field: 'title'
        },
        {
          name: 'theId',
          align: 'left',
          label: this.$t('lnpos.col_id'),
          field: 'id'
        },
        {
          name: 'key',
          align: 'left',
          label: this.$t('lnpos.col_key'),
          field: 'key'
        },
        {
          name: 'wallet',
          align: 'left',
          label: this.$t('lnpos.col_wallet'),
          field: 'wallet'
        },
        {
          name: 'currency',
          align: 'left',
          label: this.$t('lnpos.col_currency'),
          field: 'currency'
        }
      ]
    }
  },
  data() {
    return {
      protocol: window.location.protocol,
      location: window.location.hostname,
      filter: '',
      lnposs: [],
      lnposTable: {
        pagination: {
          rowsPerPage: 10
        }
      },
      formDialog: {
        show: false,
        data: {}
      }
    }
  },
  methods: {
    cancelLnpos() {
      this.formDialog.show = false
      this.clearFormDialog()
    },
    closeFormDialog() {
      this.clearFormDialog()
      this.formDialog.data = {
        is_unique: false
      }
    },
    sendFormData() {
      if (!this.formDialog.data.profit) {
        this.formDialog.data.profit = 0
      }
      if (this.formDialog.data.id) {
        this.updateLnpos(this.g.user.wallets[0].adminkey, this.formDialog.data)
      } else {
        this.createLnpos(this.g.user.wallets[0].adminkey, this.formDialog.data)
      }
    },
    createLnpos(wallet, data) {
      const updatedData = {}
      for (const property in data) {
        if (data[property]) {
          updatedData[property] = data[property]
        }
      }
      LNbits.api
        .request('POST', '/lnpos/api/v1', wallet, updatedData)
        .then(response => {
          this.lnposs.push(response.data)
          this.formDialog.show = false
          this.clearFormDialog()
        })
        .catch(LNbits.utils.notifyApiError)
    },
    getLnposs() {
      LNbits.api
        .request('GET', '/lnpos/api/v1', this.g.user.wallets[0].adminkey)
        .then(response => {
          if (response.data) {
            this.lnposs = response.data
          }
        })
        .catch(LNbits.utils.notifyApiError)
    },
    deleteLnpos(lnposId) {
      LNbits.utils
        .confirmDialog(this.$t('lnpos.delete_lnpos_confirm'))
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              '/lnpos/api/v1/' + lnposId,
              this.g.user.wallets[0].adminkey
            )
            .then(() => {
              this.lnposs = _.reject(this.lnposs, obj => obj.id === lnposId)
            })
            .catch(LNbits.utils.notifyApiError)
        })
    },
    openUpdateLnpos(lnposId) {
      const lnpos = _.findWhere(this.lnposs, {id: lnposId})
      this.formDialog.data = _.clone(lnpos)
      this.formDialog.show = true
    },
    copyDeviceString(lnposId) {
      const lnpos = _.findWhere(this.lnposs, {id: lnposId})
      const deviceString = `${this.protocol}//${this.location}/lnpos/api/v2/lnurl/${lnpos.id},${lnpos.key},${lnpos.currency}`
      this.utils.copyText(deviceString)
    },
    updateLnpos(wallet, data) {
      const updatedData = {}
      for (const property in data) {
        if (data[property]) {
          updatedData[property] = data[property]
        }
      }
      LNbits.api
        .request('PUT', '/lnpos/api/v1/' + updatedData.id, wallet, updatedData)
        .then(response => {
          this.lnposs = _.reject(this.lnposs, obj => obj.id === updatedData.id)
          this.lnposs.push(response.data)
          this.formDialog.show = false
          this.clearFormDialog()
        })
        .catch(LNbits.utils.notifyApiError)
    },
    clearFormDialog() {
      this.formDialog.data = {
        lnurl_toggle: false,
        show_message: false,
        show_ack: false,
        show_price: 'None',
        title: ''
      }
    },
    exportCSV() {
      LNbits.utils.exportCSV(this.lnposColumns, this.lnposs)
    }
  },
  created() {
    this.getLnposs()
  }
}

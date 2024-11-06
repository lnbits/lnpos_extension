window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      protocol: window.location.protocol,
      location: window.location.hostname,
      filter: '',
      currency: 'USD',
      lnurlValue: '',
      lnposs: [],
      atmLinks: [],
      lnpossObj: [],
      lnposTable: {
        columns: [
          {
            name: 'title',
            align: 'left',
            label: 'title',
            field: 'title'
          },
          {
            name: 'theId',
            align: 'left',
            label: 'id',
            field: 'id'
          },
          {
            name: 'key',
            align: 'left',
            label: 'key',
            field: 'key'
          },
          {
            name: 'wallet',
            align: 'left',
            label: 'wallet',
            field: 'wallet'
          },
          {
            name: 'currency',
            align: 'left',
            label: 'currency',
            field: 'currency'
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      passedlnurldevice: {},
      settingsDialog: {
        show: false,
        data: {}
      },
      formDialog: {
        show: false,
        data: {}
      },
      formDialog: {
        show: false,
        data: {
          lnurl_toggle: false,
          show_message: false,
          show_ack: false,
          show_price: 'None',
          device: 'pos',
          profit: 1,
          amount: 1,
          title: ''
        }
      }
    }
  },
  methods: {
    cancelLnpos() {
      self.formDialog.show = false
      self.clearFormDialog()
    },
    closeFormDialog() {
      this.clearFormDialog()
      this.formDialog.data = {
        is_unique: false
      }
    },
    sendFormData() {
      if (!self.formDialog.data.profit) {
        self.formDialog.data.profit = 0
      }
      if (self.formDialog.data.id) {
        this.updateLnpos(self.g.user.wallets[0].adminkey, self.formDialog.data)
      } else {
        this.createLnpos(self.g.user.wallets[0].adminkey, self.formDialog.data)
      }
    },

    createLnpos: function (wallet, data) {
      const updatedData = {}
      for (const property in data) {
        if (data[property]) {
          updatedData[property] = data[property]
        }
      }
      LNbits.api
        .request('POST', '/lnurldevice/api/v1/lnurlpos', wallet, updatedData)
        .then(function (response) {
          self.lnposs.push(response.data)
          self.formDialog.show = false
          self.clearFormDialog()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    getLnposs() {
      LNbits.api
        .request(
          'GET',
          '/lnurldevice/api/v1/lnurlpos',
          self.g.user.wallets[0].adminkey
        )
        .then(function (response) {
          if (response.data) {
            self.lnposs = response.data.map(maplnurldevice)
          }
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    getLnpos: function (lnurldevice_id) {
      LNbits.api
        .request(
          'GET',
          '/lnurldevice/api/v1/lnurlpos/' + lnurldevice_id,
          self.g.user.wallets[0].adminkey
        )
        .then(function (response) {
          localStorage.setItem('lnurldevice', JSON.stringify(response.data))
          localStorage.setItem('inkey', self.g.user.wallets[0].inkey)
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    deleteLnpos: function (lnurldeviceId) {
      const link = _.findWhere(this.lnposs, {id: lnurldeviceId})
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this pay link?')
        .onOk(function () {
          LNbits.api
            .request(
              'DELETE',
              '/lnurldevice/api/v1/lnurlpos/' + lnurldeviceId,
              self.g.user.wallets[0].adminkey
            )
            .then(function (response) {
              self.lnposs = _.reject(self.lnposs, function (obj) {
                return obj.id === lnurldeviceId
              })
            })
            .catch(function (error) {
              LNbits.utils.notifyApiError(error)
            })
        })
    },
    openUpdateLnpos: function (lnurldeviceId) {
      const lnurldevice = _.findWhere(this.lnposs, {
        id: lnurldeviceId
      })
      self.formDialog.data = _.clone(lnurldevice._data)
      if (lnurldevice.device == 'atm' && lnurldevice.extra == 'boltz') {
        self.boltzToggleState = true
      } else {
        self.boltzToggleState = false
      }
      self.formDialog.show = true
    },
    openSettings: function (lnurldeviceId) {
      const lnurldevice = _.findWhere(this.lnposs, {
        id: lnurldeviceId
      })
      self.settingsDialog.data = _.clone(lnurldevice._data)
      self.settingsDialog.show = true
    },
    updateLnpos: function (wallet, data) {
      const updatedData = {}
      for (const property in data) {
        if (data[property]) {
          updatedData[property] = data[property]
        }
      }

      LNbits.api
        .request(
          'PUT',
          '/lnurldevice/api/v1/lnurlpos/' + updatedData.id,
          wallet,
          updatedData
        )
        .then(function (response) {
          self.lnposs = _.reject(self.lnposs, function (obj) {
            return obj.id === updatedData.id
          })
          self.lnposs.push(response.data)
          self.formDialog.show = false
          self.clearFormDialog()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
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
      LNbits.utils.exportCSV(self.lnposTable.columns, this.lnposs)
    }
  },
  created() {
    this.getLnposs()
    LNbits.api
      .request('GET', '/api/v1/currencies')
      .then(response => {
        this.currency = ['sat', 'USD', ...response.data]
      })
      .catch(err => {
        LNbits.utils.notifyApiError(err)
      })
  }
})

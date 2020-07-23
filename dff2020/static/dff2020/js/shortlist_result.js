var app = new Vue({
    el: '#result-app',
    data: {
        error: '',
        message: '',
        attempts: []
    },
    created() {
        axios.get(`/api/shortlist/${shortlist_id}/result`)
            .then(response => {
                console.log(response)
                if (response.data.success) {
                    this.message = response.data.message
                    this.attempts = response.data.attempts
                } else {
                    this.error = response.data.error
                }
            })
            .catch(error => {
                console.log(error)
            })
    },
    methods: {
        get_time_str(secs) {
            var minutes = String(parseInt(secs / 60))
            var secs = String(parseInt(secs - minutes * 60))
            return minutes.padStart(2, '0') + ":" + secs.padStart(2, '0')
        }
    }
})
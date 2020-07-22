var app = new Vue({
    el: '#result-app',
    data: {
        error: '',
        message: '',
        winners: []
    },
    created() {
        axios.get(`/api/quiz/results`)
            .then(response => {
                console.log(response)
                if (response.data.success) {
                    this.message = response.data.message
                    this.winners = response.data.winners
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
            var hours = parseInt(secs / 3600)
            var mins = parseInt((secs - (hours * 3600)) / 60)
            var secs = parseInt(secs - (mins * 60) - (hours * 3600))
            if (hours > 0)
                return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
            return `${String(mins).padStart(2, '0')}: ${String(secs).padStart(2, '0')}`
        }
    }
})
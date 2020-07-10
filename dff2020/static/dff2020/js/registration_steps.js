var steps = new Vue({
    el: '#steps',
    data: {
        steps: [
            {
                id: 1,
                name: "Registrations Start",
                date: "June 20th",
                activate_on: moment.tz('Jun 20 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 2,
                name: "Registrations End",
                desc: "No new users will be able to create their accounts on the website after this",
                date: "June 26th",
                activate_on: moment('Jun 27 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 3,
                name: "Registrations Extended",
                desc: "Free registrations can now be done till 30th June, after which a late registration fee of ₹99 will be charged",
                date: "June 30th",
                activate_on: moment('Jun 27 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 4,
                name: "Late Registrations",
                desc: "New users can create their account on the website but a late fee of ₹99 will be charged while submission. The movie submission fee stays as is, i.e. ₹299 per entry.",
                date: "July 1st",
                activate_on: moment('Jul 01 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 5,
                name: "Late Registrations & Submissions Closed",
                desc: "No Submissions and/or registrations will be accepted after 10th July 11:59 PM",
                date: "July 10th",
                activate_on: moment('Jul 11 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 6,
                name: "Screening of top 10 Films",
                desc: "Top 10 entries hand-picked by our jury of judges will be screened across platforms of Moviepedia",
                date: "July 24th - August 1st",
                activate_on: moment('Jul 11 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 7,
                name: "Results",
                desc: "Winners will be announced on the final day of the Film Festival",
                date: "August 2nd",
                activate_on: moment('Aug 02 2020', "MMM DD YYYY", "Asia/Kolkata")
            }]
    },
    mounted() {
        $('.stepper').mdbStepper();
    },
    computed: {
        active_step_id() {
            var today = moment().tz("Asia/Kolkata")
            var active_step_id = 1
            this.steps.forEach(step => {
                if (today.isAfter(step.activate_on)) {
                    active_step_id = step.id
                }
            })
            return active_step_id;
        }
    }
})

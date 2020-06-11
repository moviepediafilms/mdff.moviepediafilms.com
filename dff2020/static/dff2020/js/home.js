new Vue({
    el: '#movies-app',
    data: {
        movies: []
    },
    mounted() {
        this.add_movie();
    },
    methods: {
        add_movie() {
            this.movies.push({ name: '', director: '', runtime: '' });
        },
        remove_movie(index) {
            console.log(index, 'deleted');
            this.movies.splice(index, 1);
        }
    }
})

function onSignIn(googleUser) {
    var profile = googleUser.getBasicProfile();
    console.log('ID: ' + profile.getId()); // Do not send to your backend! Use an ID token instead.
    console.log('Name: ' + profile.getName());
    console.log('Image URL: ' + profile.getImageUrl());
    console.log('Email: ' + profile.getEmail()); // This is null if the 'email' scope is not present.
}
function signOut() {
    var auth2 = gapi.auth2.getAuthInstance();
    auth2.signOut().then(function () {
        console.log('User signed out.');
    });
}
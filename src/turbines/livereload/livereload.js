(function () {
    // Simple livereload script: reloads the page when a message is received
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = window.location.port ? window.location.port : (protocol === 'wss:' ? 443 : 80);
    const socket = new WebSocket(`ws://${host}:8000/_turbines/livereload`);

    // send initial message to identify as livereload client
    socket.addEventListener('open', function () {
        console.log('Livereload: connected');
        socket.send('hello');
    });


    socket.addEventListener('message', function (event) {
        if (event.data === 'reload') {
            window.location.reload();
        }
    });



    socket.addEventListener('error', function () {
        console.warn('Livereload: connection error');
    });

    socket.addEventListener('close', function () {
        console.warn('Livereload: connection closed');
    });
})();
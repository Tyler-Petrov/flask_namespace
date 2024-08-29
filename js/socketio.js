// ################### Helper Funtions ###################
function snakeToCamelObj(obj) {
    const camelCaseObject = Object.fromEntries(
        Object.entries(obj).map(([key, value]) => {
            // Convert snake_case to camelCase
            const camelCaseKey = key.replace(/_([a-z])/g, (g) => g[1].toUpperCase());
            return [camelCaseKey, value];
        })
    );
    return camelCaseObject;
}

function camelToSnake(obj) {
    const snakeCaseObject = Object.fromEntries(
        Object.entries(obj).map(([key, value]) => {
            // Convert camelCase to snake_case
            const snakeCaseKey = key.replace(/([A-Z])/g, '_$1').toLowerCase();
            return [snakeCaseKey, value];
        })
    );
    return snakeCaseObject;
}


// ################### Socket IO Namespace class ###################
class SocketIONamespace {
    constructor(namespace, room) {
        this.joinedRoom = null
        this.room = room
        this.namespace = namespace
        this.socket = io(namespace, {
            ackTimeout: 10000,
            retries: 3,
        });

        this.init()
    }

    init() {
        let namespaceSocket = this

        // Join Jam Session room right after client server handshake
        namespaceSocket.on('connect', function () {
            namespaceSocket.emit('join_room');

            // Listen for response after room join
            namespaceSocket.on('join_room', function ({ joinedRoom, sid, ...data } = {}) {
                namespaceSocket.joinedRoom = joinedRoom
                // If users didn't join the room due to it being full then show the room full warning
                if (!joinedRoom) {
                    this.failedRoomJoin()
                }
            });
        });

        // Listen for global events from the server
        namespaceSocket.on('global_event', function ({ eventName, ...data } = {}) {
            if (!namespaceSocket.eventHandlers.includes(eventName)) return;
            namespaceSocket.emit(eventName, camelToSnake(data))
        });
    }

    failedRoomJoin() {
        return
    }

    on(eventName, cb) {
        return this.socket.on(eventName, function ({ ...snakeKeysData } = {}) {
            // Convert the keys of the data obj to camel case for js
            let camelKeysData = snakeToCamelObj(snakeKeysData)

            return cb(camelKeysData)
        })
    }

    emit(eventName, data = null) {
        if (data == null) data = {}
        data['room_name'] = this.room
        data = this.prepareData(eventName, data)
        this.socket.emit(eventName, data)
    }

    emitGlobalEvent(eventName, data) {
        let namespaceSocket = this

        namespaceSocket.emit('trigger_global_event', {
            'event_name': eventName,
            'room': namespaceSocket.room,
            ...data,
        })
    }

    get eventHandlers() {
        return Object.keys(this.socket._callbacks).map(key => key.replace('$', ''));
    }

    prepareData(eventName, data) {
        return data
    }
}

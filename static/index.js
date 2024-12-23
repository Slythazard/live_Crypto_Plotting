const socket = io()
price = []
time = []
graph = document.getElementById("graph");
Plotly.newPlot(graph,[{x:[time],y:[price],type:'scatter',mode:'lines+markers'}],{responsive: true})
socket.on("connect",()=>{
    socket.emit('messageOnConnection',{data:"Hi Server This is Js",id:`${socket.id}`})
})
socket.on("messageOnReceivingConnectionToClient",(data)=>{
    price.push(data.price)
    time.push(data.time)
    Plotly.update(graph,{x:[time],y:[price]})
    socket.emit('msgOnRcvConnToClntRevert')
    console.log(data)
})
socket.on('update_price',(data)=>{
    document.querySelector('#fetch #price').innerText = data.price
    document.querySelector('#fetch #time').innerHTML = data.time
    price.push(data.price)
    time.push(data.time)
    Plotly.extendTraces(graph,{x:[[data.time]],y:[[data.price]]},[0])
    // Plotly.update(graph,{x:[time],y:[price]})
})

socket.on("disconnect", () => {
    console.log("Disconnected. Attempting to reconnect...");
});
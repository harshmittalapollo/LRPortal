import { useState } from "react";
import Admin from "./Admin";
import Dashboard from "./Dashboard";
import Login from "./Login";
import "./App.css";

function App(){
const [session,setSession]=useState(null)
const [view,setView]=useState("dashboard")

function handleLogin(nextSession){
setSession(nextSession)
setView("dashboard")
}

function handleLogout(){
setSession(null)
setView("dashboard")
}

return(

<div>

{session ? (
view==="admin" ? (
<Admin session={session} onBack={()=>setView("dashboard")} onLogout={handleLogout}/>
) : (
<Dashboard session={session} onOpenAdmin={()=>setView("admin")} onLogout={handleLogout}/>
)
) : (
<Login onLogin={handleLogin}/>
)}

</div>

)

}

export default App

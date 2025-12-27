const treeEl = document.getElementById('tree')
const textarea = document.getElementById('textarea')
const pathLabel = document.getElementById('pathLabel')
let currentPath = ''

async function list(path=''){
  const res = await fetch(`/api/webshell/list?path=${encodeURIComponent(path)}`)
  const items = await res.json()
  treeEl.innerHTML = ''
  items.forEach(it=>{
    const el = document.createElement('div')
    el.textContent = it.name
    el.className = it.is_dir? 'dir file':'file'
    el.onclick = ()=>{
      if(it.is_dir){ list(it.path) }
      else { openFile(it.path) }
    }
    treeEl.appendChild(el)
  })
}

async function openFile(path){
  const res = await fetch(`/api/webshell/read?path=${encodeURIComponent(path)}`)
  const data = await res.json()
  currentPath = path
  pathLabel.textContent = path
  textarea.value = data.content||''
}

async function save(){
  if(!currentPath) return alert('No file open')
  const body = new URLSearchParams()
  body.append('path', currentPath)
  body.append('content', textarea.value)
  const res = await fetch('/api/webshell/save', {method:'POST', body})
  const data = await res.json()
  if(data.ok) alert('Saved')
  else alert('Save failed')
}

document.getElementById('refresh').onclick = ()=> list('')
document.getElementById('save').onclick = save

list('')

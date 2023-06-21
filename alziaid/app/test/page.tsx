export default async function Testpage(){
    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-12">
        <div className="z-10 w-full max-w-5xl items-center justify-center font-mono text-sm lg:flex">
            <div class="box-border h-16 w-32 p-4 border-4">
                Go Back 
            </div>
            <div class="px-8"></div>
            <div class="box-border h-32 w-64 p-4 border-4">
                Time remaining: 
            </div>
            <div class="px-8"></div>
            <div class="box-border h-32 w-64 p-4 border-4">
                Responsiveness: 
            </div>
            <div class="px-8"></div>
            <div class="box-border h-32 w-64 p-4 border-4">
                 AD index: 
            </div>
            <div class="px-8"></div>

      </div>
      <div class="py-1"></div>
      
      <div class=" shadow-2xl box-border grow min-w-full min-h-full p-4 border-4">      
                placeholder camera     
      </div>
      <div class="py-1"></div>
      <a
          href="https://vercel.com/new?utm_source=create-next-app&utm_medium=appdir-template&utm_campaign=create-next-app"
          className="group rounded-lg border border-transparent px-1 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30"
          target="_blank"
          rel="noopener noreferrer"
        >
          <h2 className={`mb-3 text-2xl font-semibold`}>
            End test{' '}
          </h2>
        </a>

      
    </main>
    );
}
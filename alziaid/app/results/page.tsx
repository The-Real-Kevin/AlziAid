
import Link from 'next/link';

export default async function Testpage(){
    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-12">
        <div className="z-10 w-full max-w-5xl items-center justify-center font-mono text-sm lg:flex">
        
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
      <a>
          <h2 className={`mb-3 text-2xl font-semibold`}>
          <Link href="/">Go Home </Link>
          </h2>
        </a>

    </main>
    );
}